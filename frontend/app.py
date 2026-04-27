import streamlit as st
import requests
import os

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="ロシア語業務翻訳アプリ", layout="wide")
st.title("🇷🇺 ロシア語ドキュメント OCR & 翻訳システム")

if "extracted_text" not in st.session_state:
    st.session_state.extracted_text = ""
if "translated_text" not in st.session_state:
    st.session_state.translated_text = ""

# --- Step 1: ファイルアップロード & テキスト抽出 ---
st.header("1. ドキュメントのアップロードとテキスト抽出")
# PDFも受け付けるように変更
uploaded_file = st.file_uploader(
    "ロシア語のファイル（画像またはPDF）をアップロード", 
    type=["jpg", "jpeg", "png", "pdf"]
)

if uploaded_file is not None:
    # 画像ファイルの場合はプレビューを表示
    if uploaded_file.type in ["image/jpeg", "image/png"]:
        st.image(uploaded_file, caption="アップロードされた画像", width=500)
    elif uploaded_file.type == "application/pdf":
        st.info("📄 PDFファイルがアップロードされました。")
    
    if st.button("テキスト抽出を実行"):
        with st.spinner("ドキュメントを解析中..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            
            # ファイルの拡張子によってAPIを切り替え
            if uploaded_file.name.lower().endswith(".pdf"):
                endpoint = f"{BACKEND_URL}/api/extract/pdf"
            else:
                endpoint = f"{BACKEND_URL}/api/ocr/image"

            res = requests.post(endpoint, files=files)
            
            if res.status_code == 200:
                result_data = res.json()
                st.session_state.extracted_text = result_data.get("extracted_text", "")
                
                # PDFの場合は、どちらの手法で抽出されたかバッジを表示すると親切です
                method = result_data.get("method")
                if method == "digital_extraction":
                    st.success("テキスト抽出に成功しました！（高速モード：デジタルPDF）")
                elif method == "vision_ocr":
                    st.success("テキスト抽出に成功しました！（OCRモード：スキャンPDF）")
                else:
                    st.success("テキストの抽出に成功しました！")
            else:
                st.error(f"抽出エラー: {res.text}")

# --- Step 2: テキストの手動編集 ---
st.header("2. テキストの確認・手動編集")
st.info("抽出の誤認識があれば、ここで直接テキストを修正してください。")
edited_text = st.text_area("抽出されたロシア語テキスト", value=st.session_state.extracted_text, height=200)

st.session_state.extracted_text = edited_text

# --- Step 3: 翻訳 ---
st.header("3. LLM (Cloud Translation) による翻訳")
if st.button("ロシア語から日本語に翻訳"):
    if not st.session_state.extracted_text.strip():
        st.warning("翻訳するテキストがありません。")
    else:
        with st.spinner("Google Cloud Translation APIで翻訳中..."):
            payload = {"text": st.session_state.extracted_text}
            res = requests.post(f"{BACKEND_URL}/api/translate/text", json=payload)
            
            if res.status_code == 200:
                st.session_state.translated_text = res.json().get("translated_text", "")
                st.success("翻訳が完了しました！")
            else:
                st.error(f"翻訳エラー: {res.text}")

if st.session_state.translated_text:
    st.text_area("日本語翻訳結果", value=st.session_state.translated_text, height=200)

    # --- Step 4: ダウンロード ---
    st.header("4. 結果のダウンロード")
    st.download_button(
        label="📄 翻訳結果をテキスト(txt)でダウンロード",
        data=st.session_state.translated_text,
        file_name="translated_result.txt",
        mime="text/plain"
    )