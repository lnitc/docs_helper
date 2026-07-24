from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from google.cloud import vision
from google.cloud import translate
import os
import io
from PIL import Image
import fitz

app = FastAPI()

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "your-project-id")
vision_client = vision.ImageAnnotatorClient()
translate_client = translate.TranslationServiceClient()

A4_WIDTH = 595
A4_HEIGHT = 842

# 画像グリッド印刷用のA4寸法（ミリメートル、縦向き）
A4_WIDTH_MM = 210.0
A4_HEIGHT_MM = 297.0
# 印刷解像度（DPI）。1mmあたりのピクセル数は DPI / 25.4
GRID_DPI = 300


def _grid_layout(size_mm: float, gap_mm: float):
    """A4縦1ページに指定サイズの正方形画像を何枚並べられるかを計算する。

    余白（gap）は画像同士の間隔として扱い、グリッド全体をページ中央に配置する。
    戻り値は (列数, 行数, 最大枚数)。
    """
    if size_mm <= 0:
        raise ValueError("画像サイズは0より大きい値を指定してください。")
    if gap_mm < 0:
        raise ValueError("余白は0以上の値を指定してください。")

    def _count(available: float) -> int:
        # n枚並べるのに必要な長さ: n*size + (n-1)*gap <= available
        return int((available + gap_mm) // (size_mm + gap_mm))

    cols = _count(A4_WIDTH_MM)
    rows = _count(A4_HEIGHT_MM)
    return cols, rows, cols * rows

# Document Translation API（translate_document）がサポートする形式
DOCUMENT_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
# オンライン（同期）ドキュメント翻訳のファイルサイズ上限
MAX_DOCUMENT_BYTES = 20 * 1024 * 1024


def _run_vision_ocr(content: bytes, language_code: str = "en") -> str:
    image = vision.Image(content=content)
    response = vision_client.document_text_detection(
        image=image,
        image_context={"language_hints": [language_code]}
    )
    if response.error.message:
        raise Exception(response.error.message)
    return response.full_text_annotation.text if response.full_text_annotation else ""


def _pdf_page_to_jpeg(page) -> bytes:
    pix = page.get_pixmap(dpi=150, colorspace=fitz.csRGB, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)

    # Vision API のインラインコンテンツ上限は約10MB
    MAX_BYTES = 10 * 1024 * 1024
    if buf.tell() > MAX_BYTES:
        scale = (MAX_BYTES / buf.tell()) ** 0.5
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80, optimize=True)

    return buf.getvalue()


@app.get("/api/languages")
async def get_supported_languages():
    try:
        parent = f"projects/{PROJECT_ID}/locations/global"
        response = translate_client.get_supported_languages(
            request={"parent": parent, "display_language_code": "ja"}
        )
        languages = [
            {"code": lang.language_code, "name": lang.display_name}
            for lang in response.languages
            if lang.support_source and lang.support_target
        ]
        return {"languages": sorted(languages, key=lambda x: x["name"])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/convert/images-to-pdf")
async def images_to_pdf(files: list[UploadFile] = File(...), normalize: str = Form("false")):
    try:
        normalize_flag = normalize.lower() == "true"
        scale = fitz.Matrix(2, 2) if normalize_flag else fitz.Matrix(1, 1)

        all_images = []
        for file in files:
            content = await file.read()
            if file.content_type == "application/pdf" or (file.filename and file.filename.lower().endswith(".pdf")):
                pdf_document = fitz.open(stream=content, filetype="pdf")
                for page in pdf_document:
                    pix = page.get_pixmap(matrix=scale)
                    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    all_images.append(img)
            else:
                img = Image.open(io.BytesIO(content)).convert('RGB')
                all_images.append(img)

        if not all_images:
            raise HTTPException(status_code=400, detail="有効なデータがありません")

        pdf_bytes = io.BytesIO()
        if normalize_flag:
            canvas_size = (A4_WIDTH * 2, A4_HEIGHT * 2)
            pages = []
            for img in all_images:
                canvas = Image.new('RGB', canvas_size, (255, 255, 255))
                img.thumbnail(canvas_size, Image.Resampling.LANCZOS)
                offset = ((canvas.width - img.width) // 2, (canvas.height - img.height) // 2)
                canvas.paste(img, offset)
                pages.append(canvas)
            pages[0].save(pdf_bytes, format='PDF', save_all=True, append_images=pages[1:], resolution=100.0)
        else:
            all_images[0].save(pdf_bytes, format='PDF', save_all=True, append_images=all_images[1:], resolution=72.0)

        pdf_bytes.seek(0)
        return Response(content=pdf_bytes.read(), media_type="application/pdf")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/images/grid-capacity")
async def grid_capacity(size_mm: float = 58.0, gap_mm: float = 2.0):
    """指定した画像サイズ・余白でA4縦1ページに収まる最大枚数を返す。"""
    try:
        cols, rows, max_images = _grid_layout(size_mm, gap_mm)
        return {"columns": cols, "rows": rows, "max_images": max_images}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _center_crop_square(img: Image.Image) -> Image.Image:
    """画像を中央基準で正方形に切り抜く。"""
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side))


@app.post("/api/images/grid-to-pdf")
async def images_grid_to_pdf(
    files: list[UploadFile] = File(...),
    size_mm: str = Form("58"),
    gap_mm: str = Form("2"),
):
    """正方形画像を指定mmに縮小し、A4縦1ページのグリッドに配置したPDFを返す。"""
    try:
        try:
            size_val = float(size_mm)
            gap_val = float(gap_mm)
        except ValueError:
            raise HTTPException(status_code=400, detail="サイズ・余白は数値で指定してください。")

        try:
            cols, rows, max_images = _grid_layout(size_val, gap_val)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if max_images < 1:
            raise HTTPException(
                status_code=400,
                detail="指定サイズが大きすぎてA4に1枚も配置できません。",
            )

        if len(files) > max_images:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"画像が多すぎます。{size_val:g}mm・余白{gap_val:g}mmでは"
                    f"A4に最大{max_images}枚（{cols}列×{rows}行）まで配置できます。"
                    f"現在{len(files)}枚選択されています。"
                ),
            )

        px_per_mm = GRID_DPI / 25.4
        size_px = round(size_val * px_per_mm)
        gap_px = round(gap_val * px_per_mm)
        page_w = round(A4_WIDTH_MM * px_per_mm)
        page_h = round(A4_HEIGHT_MM * px_per_mm)

        canvas = Image.new("RGB", (page_w, page_h), (255, 255, 255))

        # グリッド全体をページ中央に配置するためのオフセットを計算
        grid_w = cols * size_px + (cols - 1) * gap_px
        grid_h = rows * size_px + (rows - 1) * gap_px
        origin_x = (page_w - grid_w) // 2
        origin_y = (page_h - grid_h) // 2

        for idx, file in enumerate(files):
            content = await file.read()
            img = Image.open(io.BytesIO(content)).convert("RGB")
            img = _center_crop_square(img)
            img = img.resize((size_px, size_px), Image.LANCZOS)

            col = idx % cols
            row = idx // cols
            x = origin_x + col * (size_px + gap_px)
            y = origin_y + row * (size_px + gap_px)
            canvas.paste(img, (x, y))

        pdf_bytes = io.BytesIO()
        canvas.save(pdf_bytes, format="PDF", resolution=float(GRID_DPI))
        pdf_bytes.seek(0)
        return Response(content=pdf_bytes.read(), media_type="application/pdf")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ocr/image")
async def ocr_image(file: UploadFile = File(...), language: str = Form("en")):
    try:
        content = await file.read()
        return {"extracted_text": _run_vision_ocr(content, language)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/extract/pdf")
async def extract_pdf(file: UploadFile = File(...), language: str = Form("en")):
    try:
        content = await file.read()
        doc = fitz.open(stream=content, filetype="pdf")

        digital_text = "\n".join(page.get_text() for page in doc)
        if len(digital_text.strip()) > 50:
            return {"extracted_text": digital_text.strip(), "method": "digital_extraction"}

        ocr_text = "\n".join(_run_vision_ocr(_pdf_page_to_jpeg(page), language) for page in doc)
        return {"extracted_text": ocr_text.strip(), "method": "vision_ocr"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/translate/text")
async def translate_text(payload: dict):
    text = payload.get("text", "")
    if not text:
        return {"translated_text": ""}

    source_language = payload.get("source_language", "en")
    target_language = payload.get("target_language", "ja")

    try:
        parent = f"projects/{PROJECT_ID}/locations/global"
        response = translate_client.translate_text(
            request={
                "parent": parent,
                "contents": [text],
                "mime_type": "text/plain",
                "source_language_code": source_language,
                "target_language_code": target_language,
            }
        )
        return {"translated_text": response.translations[0].translated_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/translate/document")
async def translate_document(
    file: UploadFile = File(...),
    source_language: str = Form("en"),
    target_language: str = Form("ja"),
):
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    mime_type = DOCUMENT_MIME_TYPES.get(ext)
    if mime_type is None:
        supported = ", ".join(sorted(DOCUMENT_MIME_TYPES))
        raise HTTPException(
            status_code=400,
            detail=f"対応していないファイル形式です。対応形式: {supported}",
        )

    content = await file.read()
    if len(content) > MAX_DOCUMENT_BYTES:
        raise HTTPException(
            status_code=400,
            detail="ファイルサイズが20MBを超えています（オンライン翻訳の上限）。",
        )

    try:
        parent = f"projects/{PROJECT_ID}/locations/global"
        request = {
            "parent": parent,
            "source_language_code": source_language,
            "target_language_code": target_language,
            "document_input_config": {"content": content, "mime_type": mime_type},
        }

        response = translate_client.translate_document(request=request)
        translated_bytes = b"".join(
            chunk for chunk in response.document_translation.byte_stream_outputs
        )

        base_name = os.path.splitext(os.path.basename(filename))[0] or "document"
        download_name = f"translated_{base_name}{ext}"

        return Response(
            content=translated_bytes,
            media_type=mime_type,
            headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
