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
vision_client = vision.ImageAnnotatorClient()
translate_client = translate.TranslationServiceClient()

A4_WIDTH = 595
A4_HEIGHT = 842


def _run_vision_ocr(content: bytes) -> str:
    image = vision.Image(content=content)
    response = vision_client.document_text_detection(
        image=image,
        image_context={"language_hints": ["ru"]}
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


@app.post("/api/convert/images-to-pdf")
async def images_to_pdf(files: list[UploadFile] = File(...)):
    try:
        all_images = []
        for file in files:
            content = await file.read()
            if file.content_type == "application/pdf" or (file.filename and file.filename.lower().endswith(".pdf")):
                pdf_document = fitz.open(stream=content, filetype="pdf")
                for page in pdf_document:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    all_images.append(img)
            else:
                img = Image.open(io.BytesIO(content)).convert('RGB')
                all_images.append(img)

        if not all_images:
            raise HTTPException(status_code=400, detail="有効なデータがありません")

        canvas_size = (A4_WIDTH * 2, A4_HEIGHT * 2)
        processed_pages = []
        for img in all_images:
            canvas = Image.new('RGB', canvas_size, (255, 255, 255))
            img.thumbnail(canvas_size, Image.Resampling.LANCZOS)
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
    try:
        content = await file.read()
        return {"extracted_text": _run_vision_ocr(content)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/extract/pdf")
async def extract_pdf(file: UploadFile = File(...)):
    try:
        content = await file.read()
        doc = fitz.open(stream=content, filetype="pdf")

        digital_text = "\n".join(page.get_text() for page in doc)
        if len(digital_text.strip()) > 50:
            return {"extracted_text": digital_text.strip(), "method": "digital_extraction"}

        ocr_text = "\n".join(_run_vision_ocr(_pdf_page_to_jpeg(page)) for page in doc)
        return {"extracted_text": ocr_text.strip(), "method": "vision_ocr"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/translate/text")
async def translate_text(payload: dict):
    text = payload.get("text", "")
    if not text:
        return {"translated_text": ""}

    try:
        parent = f"projects/{PROJECT_ID}/locations/global"
        response = translate_client.translate_text(
            request={
                "parent": parent,
                "contents": [text],
                "mime_type": "text/plain",
                "source_language_code": "ru",
                "target_language_code": "ja",
            }
        )
        return {"translated_text": response.translations[0].translated_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
