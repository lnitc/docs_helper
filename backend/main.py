from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
from google.cloud import vision
from google.cloud import translate
import os
import io
from PIL import Image

app = FastAPI()

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "your-project-id")

@app.post("/api/ocr/image")
async def ocr_image(file: UploadFile = File(...)):
    """画像のロシア語筆記体をOCRでテキスト化"""
    try:
        content = await file.read()
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=content)
        
        # 筆記体や文書に強い document_text_detection を使用
        response = client.document_text_detection(
            image=image,
            image_context={"language_hints": ["ru"]} # ロシア語を指定
        )
        
        if response.error.message:
            raise Exception(response.error.message)

        text = response.full_text_annotation.text
        return {"extracted_text": text}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/translate/text")
async def translate_text(payload: dict):
    """テキストをロシア語から日本語へ翻訳 (Cloud Translation Advanced v3)"""
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


@app.post("/api/convert/images-to-pdf")
async def images_to_pdf(files: list[UploadFile] = File(...)):
    """複数のJPEGを1つのPDFに変換"""
    try:
        images = []
        for file in files:
            content = await file.read()
            img = Image.open(io.BytesIO(content)).convert('RGB')
            images.append(img)
            
        if not images:
            raise HTTPException(status_code=400, detail="画像がありません")

        pdf_bytes = io.BytesIO()
        # 1枚目をベースに、残りをappendしていく
        images[0].save(pdf_bytes, format='PDF', save_all=True, append_images=images[1:])
        pdf_bytes.seek(0)
        
        return Response(content=pdf_bytes.read(), media_type="application/pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))