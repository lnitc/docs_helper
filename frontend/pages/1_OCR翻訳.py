import streamlit as st
import requests
import os

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

if "ocr_reset_key" not in st.session_state:
    st.session_state.ocr_reset_key = 0
if "translated_text" not in st.session_state:
    st.session_state.translated_text = ""

textarea_key = f"ocr_textarea_{st.session_state.ocr_reset_key}"

col_title, col_btn = st.columns([4, 1])
with col_title:
    st.title("ロシア語ドキュメント OCR & 翻訳")
with col_btn:
    st.write("")
    if st.button("クリア", key="ocr_clear"):
        st.session_state.ocr_reset_key += 1
        st.session_state.translated_text = ""
        st.rerun()

st.header("1. ドキュメントのアップロードとテキスト抽出")
uploaded_file = st.file_uploader(
    "ロシア語のファイル（画像またはPDF）をアップロード",
    type=["jpg", "jpeg", "png", "pdf"],
    key=f"ocr_file_{st.session_state.ocr_reset_key}"
)

if uploaded_file is not None:
    if uploaded_file.type in ["image/jpeg", "image/png"]:
        st.image(uploaded_file, caption="アップロードされた画像", width=500)
    elif uploaded_file.type == "application/pdf":
        st.info("PDFファイルがアップロードされました。")

    if st.button("テキスト抽出を実行"):
        with st.spinner("ドキュメントを解析中..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}

            if uploaded_file.name.lower().endswith(".pdf"):
                endpoint = f"{BACKEND_URL}/api/extract/pdf"
            else:
                endpoint = f"{BACKEND_URL}/api/ocr/image"

            res = requests.post(endpoint, files=files)

            if res.status_code == 200:
                result_data = res.json()
                # keyのsession stateに直接書き込む（valueパラメータとの競合を回避）
                st.session_state[textarea_key] = result_data.get("extracted_text", "")

                method = result_data.get("method")
                if method == "digital_extraction":
                    st.success("テキスト抽出に成功しました！（高速モード：デジタルPDF）")
                elif method == "vision_ocr":
                    st.success("テキスト抽出に成功しました！（OCRモード：スキャンPDF）")
                else:
                    st.success("テキストの抽出に成功しました！")
            else:
                st.error(f"抽出エラー: {res.text}")

st.header("2. テキストの確認・手動編集")
st.info("抽出の誤認識があれば、ここで直接テキストを修正してください。")
st.text_area(
    "抽出されたロシア語テキスト",
    height=200,
    key=textarea_key
)

st.header("3. Cloud Translation による翻訳")
if st.button("ロシア語から日本語に翻訳"):
    current_text = st.session_state.get(textarea_key, "")
    if not current_text.strip():
        st.warning("翻訳するテキストがありません。")
    else:
        with st.spinner("Google Cloud Translation APIで翻訳中..."):
            payload = {"text": current_text}
            res = requests.post(f"{BACKEND_URL}/api/translate/text", json=payload)

            if res.status_code == 200:
                st.session_state.translated_text = res.json().get("translated_text", "")
                st.success("翻訳が完了しました！")
            else:
                st.error(f"翻訳エラー: {res.text}")

if st.session_state.translated_text:
    st.text_area("日本語翻訳結果", value=st.session_state.translated_text, height=200)

    st.header("4. 結果のダウンロード")
    st.download_button(
        label="翻訳結果をテキスト(txt)でダウンロード",
        data=st.session_state.translated_text,
        file_name="translated_result.txt",
        mime="text/plain"
    )
