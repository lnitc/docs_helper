import streamlit as st
import requests
import os

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


@st.cache_data
def fetch_languages(backend_url: str):
    try:
        res = requests.get(f"{backend_url}/api/languages")
        if res.status_code == 200:
            return res.json().get("languages", [])
    except Exception:
        pass
    return []


if "ocr_reset_key" not in st.session_state:
    st.session_state.ocr_reset_key = 0
if "translated_text" not in st.session_state:
    st.session_state.translated_text = ""

textarea_key = f"ocr_textarea_{st.session_state.ocr_reset_key}"

col_title, col_btn = st.columns([4, 1])
with col_title:
    st.title("ドキュメント OCR & 翻訳")
with col_btn:
    st.write("")
    if st.button("クリア", key="ocr_clear"):
        st.session_state.ocr_reset_key += 1
        st.session_state.translated_text = ""
        st.rerun()

languages = fetch_languages(BACKEND_URL)
if languages:
    lang_names = [lang["name"] for lang in languages]
    lang_codes = {lang["name"]: lang["code"] for lang in languages}

    default_src = next((i for i, l in enumerate(languages) if l["code"] == "en"), 0)
    default_tgt = next((i for i, l in enumerate(languages) if l["code"] == "ja"), 0)

    col_src, col_tgt = st.columns(2)
    with col_src:
        source_lang_name = st.selectbox("原文言語（OCR・翻訳元）", lang_names, index=default_src, key="src_lang")
    with col_tgt:
        target_lang_name = st.selectbox("翻訳先言語", lang_names, index=default_tgt, key="tgt_lang")

    source_lang = lang_codes[source_lang_name]
    target_lang = lang_codes[target_lang_name]
else:
    st.warning("言語リストの取得に失敗しました。バックエンドへの接続を確認してください。")
    source_lang = "en"
    target_lang = "ja"

st.header("1. ドキュメントのアップロードとテキスト抽出")
uploaded_file = st.file_uploader(
    "ファイル（画像またはPDF）をアップロード",
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
            data = {"language": source_lang}

            if uploaded_file.name.lower().endswith(".pdf"):
                endpoint = f"{BACKEND_URL}/api/extract/pdf"
            else:
                endpoint = f"{BACKEND_URL}/api/ocr/image"

            res = requests.post(endpoint, files=files, data=data)

            if res.status_code == 200:
                result_data = res.json()
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
    "抽出されたテキスト",
    height=200,
    key=textarea_key
)

st.header("3. Cloud Translation による翻訳")
if st.button("翻訳を実行"):
    current_text = st.session_state.get(textarea_key, "")
    if not current_text.strip():
        st.warning("翻訳するテキストがありません。")
    else:
        with st.spinner("Google Cloud Translation APIで翻訳中..."):
            payload = {
                "text": current_text,
                "source_language": source_lang,
                "target_language": target_lang,
            }
            res = requests.post(f"{BACKEND_URL}/api/translate/text", json=payload)

            if res.status_code == 200:
                st.session_state.translated_text = res.json().get("translated_text", "")
                st.success("翻訳が完了しました！")
            else:
                st.error(f"翻訳エラー: {res.text}")

if st.session_state.translated_text:
    st.text_area("翻訳結果", value=st.session_state.translated_text, height=200)

    st.header("4. 結果のダウンロード")
    st.download_button(
        label="翻訳結果をテキスト(txt)でダウンロード",
        data=st.session_state.translated_text,
        file_name="translated_result.txt",
        mime="text/plain"
    )
