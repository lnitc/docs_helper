from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
from google.cloud import vision
from google.cloud import translate
import os
import io
from PIL import Image
import fitz

app = FastAPI()

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "your-project-id")

A4_WIDTH = 595
A4_HEIGHT = 842

@app.post("/api/convert/images-to-pdf")
async def images_to_pdf(files: list[UploadFile] = File(...)):
    try:
        all_images = []
        for file in files:
            content = await file.read()
            if file.content_type == "application/pdf" or (file.filename and file.filename.lower().endswith(".pdf")):
                pdf_document = fitz.open(stream=content, filetype="pdf")
                for page_num in range(len(pdf_document)):
                    page = pdf_document.load_page(page_num)
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img = Image.frombytes("RGB", (int(pix.width), int(pix.height)), pix.samples)
                    all_images.append(img)
            else:
                img = Image.open(io.BytesIO(content)).convert('RGB')
                all_images.append(img)

        if not all_images:
            raise HTTPException(status_code=400, detail="有効なデータがありません")

        processed_pages = []
        for img in all_images:
            canvas = Image.new('RGB', (A4_WIDTH * 2, A4_HEIGHT * 2), (255, 255, 255))
            img.thumbnail((A4_WIDTH * 2, A4_HEIGHT * 2), Image.Resampling.LANCZOS)
            offset = ((canvas.width - img.width) // 2, (canvas.height - img.height) // 2)
            canvas.paste(img, offset)
            processed_pages.append(canvas)

        pdf_bytes = io.BytesIO()
        processed_pages[0].save(
            pdf_bytes,
            format='PDF',
            save_all=True,
            append_images=processed_pages[1:],
            resolution=100.0
        )
        pdf_bytes.seek(0)
        return Response(content=pdf_bytes.read(), media_type="application/pdf")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ocr/image")
async def ocr_image(file: UploadFile = File(...)):
    """画像のロシア語筆記体をOCRでテキスト化"""
    try:
        content = await file.read()
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=content)
        
        response = client.document_text_detection(
            image=image,
            image_context={"language_hints": ["ru"]}
        )
        
        if response.error.message:
            raise Exception(response.error.message)

        text = response.full_text_annotation.text if response.full_text_annotation else ""
        return {"extracted_text": text}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/extract/pdf")
async def extract_pdf(file: UploadFile = File(...)):
    """PDFからテキストを抽出（デジタル/スキャン自動判定）"""
    try:
        content = await file.read()
        # メモリ上でPDFを開く
        doc = fitz.open(stream=content, filetype="pdf")
        
        # 1. まずはテキスト埋め込み（デジタルPDF）として抽出を試みる
        extracted_text = ""
        for page in doc:
            extracted_text += page.get_text() + "\n"
        
        # テキストが一定量以上あれば「デジタルPDF」と判定して終了
        # （※閾値の50文字は目安です。運用に合わせて調整してください）
        if len(extracted_text.strip()) > 50:
            return {
                "extracted_text": extracted_text.strip(),
                "method": "digital_extraction"
            }
        
        # 2. テキストが抽出できなければ「スキャンPDF」と判定し、OCRへフォールバック
        client = vision.ImageAnnotatorClient()
        ocr_text = ""

        # Vision API のインラインコンテンツ上限は約10MB
        MAX_IMAGE_BYTES = 10 * 1024 * 1024

        for page in doc:
            # 150 DPI はOCR精度を保ちつつサイズを抑えるバランス値
            # alpha=False でアルファチャンネルを除去し、常に3バイト/画素(RGB)を保証する
            pix = page.get_pixmap(dpi=150, colorspace=fitz.csRGB, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            img_buffer = io.BytesIO()
            img.save(img_buffer, format="JPEG", quality=85, optimize=True)

            # それでも上限を超える場合は画像を縮小
            if img_buffer.tell() > MAX_IMAGE_BYTES:
                scale = (MAX_IMAGE_BYTES / img_buffer.tell()) ** 0.5
                new_size = (int(img.width * scale), int(img.height * scale))
                img = img.resize(new_size, Image.LANCZOS)
                img_buffer = io.BytesIO()
                img.save(img_buffer, format="JPEG", quality=80, optimize=True)

            img_bytes = img_buffer.getvalue()

            image = vision.Image(content=img_bytes)
            response = client.document_text_detection(
                image=image,
                image_context={"language_hints": ["ru"]}
            )
            
            if response.error.message:
                raise Exception(response.error.message)
            
            if response.full_text_annotation:
                ocr_text += response.full_text_annotation.text + "\n"
                
        return {
            "extracted_text": ocr_text.strip(),
            "method": "vision_ocr"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/translate/text")
async def translate_text(payload: dict):
    # 既存のまま変更なし
    text = payload.get("text", "")
    if not text:
        return {"translated_text": ""}

    try:
        client = translate.TranslationServiceClient()
        location = "global"
        parent = f"projects/{PROJECT_ID}/locations/{location}"

        response = client.translate_text(
            request={
                "parent": parent,
                "contents": [text],
                "mime_type": "text/plain",
                "source_language_code": "ru",
                "target_language_code": "ja",
            }
        )
        translated = response.translations[0].translated_text
        return {"translated_text": translated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
