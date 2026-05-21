import streamlit as st
import requests
import os

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

if "pdf_reset_key" not in st.session_state:
    st.session_state.pdf_reset_key = 0
if "pdf_result" not in st.session_state:
    st.session_state.pdf_result = None

col_title, col_btn = st.columns([4, 1])
with col_title:
    st.title("PDFコンパイラ")
with col_btn:
    st.write("")
    if st.button("クリア", key="pdf_clear"):
        st.session_state.pdf_reset_key += 1
        st.session_state.pdf_result = None
        st.rerun()

st.write("複数の画像やPDFファイルを1つのPDFにまとめます。")

st.header("1. ファイルのアップロード")
uploaded_files = st.file_uploader(
    "画像またはPDFを選択してください（複数選択可）",
    type=["jpg", "jpeg", "png", "pdf"],
    accept_multiple_files=True,
    key=f"pdf_files_{st.session_state.pdf_reset_key}"
)

if uploaded_files:
    st.info(f"{len(uploaded_files)} 件のファイルが選択されています。")

normalize = st.checkbox(
    "画像サイズの調整（A4サイズに統一・中央配置）",
    value=True,
    key=f"pdf_normalize_{st.session_state.pdf_reset_key}"
)

if st.button("PDFを作成", disabled=not uploaded_files):
    st.session_state.pdf_result = None
    with st.spinner("PDFを作成中..."):
        files_to_send = [
            ("files", (f.name, f.getvalue(), f.type))
            for f in uploaded_files
        ]
        res = requests.post(
            f"{BACKEND_URL}/api/convert/images-to-pdf",
            files=files_to_send,
            data={"normalize": str(normalize).lower()}
        )

        if res.status_code == 200:
            st.session_state.pdf_result = res.content
        else:
            st.error(f"変換エラー: {res.text}")

if st.session_state.pdf_result:
    st.success("PDFの作成が完了しました！")
    st.download_button(
        label="PDFをダウンロード",
        data=st.session_state.pdf_result,
        file_name="compiled.pdf",
        mime="application/pdf"
    )
