import streamlit as st
import requests
import os

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

DOCUMENT_TYPES = ["pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx"]


@st.cache_data
def fetch_languages(backend_url: str):
    try:
        res = requests.get(f"{backend_url}/api/languages")
        if res.status_code == 200:
            return res.json().get("languages", [])
    except Exception:
        pass
    return []


if "doctrans_reset_key" not in st.session_state:
    st.session_state.doctrans_reset_key = 0
if "doctrans_result" not in st.session_state:
    st.session_state.doctrans_result = None
if "doctrans_filename" not in st.session_state:
    st.session_state.doctrans_filename = None
if "doctrans_mime" not in st.session_state:
    st.session_state.doctrans_mime = None

col_title, col_btn = st.columns([4, 1])
with col_title:
    st.title("ドキュメント翻訳（レイアウト保持）")
with col_btn:
    st.write("")
    if st.button("クリア", key="doctrans_clear"):
        st.session_state.doctrans_reset_key += 1
        st.session_state.doctrans_result = None
        st.session_state.doctrans_filename = None
        st.session_state.doctrans_mime = None
        st.rerun()

st.info(
    "Word・PowerPoint・Excel・PDFファイルを、**元のレイアウトや書式を保ったまま丸ごと翻訳**します"
    "（Google Cloud Document Translation API）。テキストの抽出や手動編集は行わず、"
    "翻訳済みのドキュメントがそのまま出力されます。\n\n"
    "画像やスキャンPDFからテキストを抽出し、内容を手動で確認・修正しながら翻訳したい場合は、"
    "「OCR & 翻訳」ページをご利用ください。"
)

languages = fetch_languages(BACKEND_URL)
if languages:
    lang_names = [lang["name"] for lang in languages]
    lang_codes = {lang["name"]: lang["code"] for lang in languages}

    default_src = next((i for i, l in enumerate(languages) if l["code"] == "en"), 0)
    default_tgt = next((i for i, l in enumerate(languages) if l["code"] == "ja"), 0)

    col_src, col_tgt = st.columns(2)
    with col_src:
        source_lang_name = st.selectbox("原文言語", lang_names, index=default_src, key="doctrans_src_lang")
    with col_tgt:
        target_lang_name = st.selectbox("翻訳先言語", lang_names, index=default_tgt, key="doctrans_tgt_lang")

    source_lang = lang_codes[source_lang_name]
    target_lang = lang_codes[target_lang_name]
else:
    st.warning("言語リストの取得に失敗しました。バックエンドへの接続を確認してください。")
    source_lang = "en"
    target_lang = "ja"

st.header("1. ドキュメントのアップロード")
st.caption(
    "対応形式: PDF・Word（doc/docx）・PowerPoint（ppt/pptx）・Excel（xls/xlsx）　"
    "ファイルサイズ上限: 20MB（ネイティブPDFは300ページ、スキャンPDFは20ページまで）"
)
uploaded_file = st.file_uploader(
    "ファイルをアップロード",
    type=DOCUMENT_TYPES,
    key=f"doctrans_file_{st.session_state.doctrans_reset_key}"
)

st.header("2. 翻訳の実行")
if st.button("翻訳を実行", disabled=uploaded_file is None):
    st.session_state.doctrans_result = None
    with st.spinner("Document Translation APIでドキュメントを翻訳中..."):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        data = {
            "source_language": source_lang,
            "target_language": target_lang,
        }
        res = requests.post(f"{BACKEND_URL}/api/translate/document", files=files, data=data)

        if res.status_code == 200:
            base_name, ext = os.path.splitext(uploaded_file.name)
            mime = res.headers.get("Content-Type", uploaded_file.type)

            st.session_state.doctrans_result = res.content
            st.session_state.doctrans_filename = f"translated_{base_name}{ext}"
            st.session_state.doctrans_mime = mime
        else:
            st.error(f"翻訳エラー: {res.text}")

if st.session_state.doctrans_result:
    st.success("翻訳が完了しました！レイアウト・書式は元のドキュメントのまま保持されています。")

    st.header("3. 結果のダウンロード")
    st.download_button(
        label="翻訳済みドキュメントをダウンロード",
        data=st.session_state.doctrans_result,
        file_name=st.session_state.doctrans_filename,
        mime=st.session_state.doctrans_mime,
    )
