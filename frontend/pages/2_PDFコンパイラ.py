import streamlit as st
import requests
import os

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

st.title("PDFコンパイラ")
st.write("複数の画像やPDFファイルを1つのPDFにまとめます。")

st.header("1. ファイルのアップロード")
uploaded_files = st.file_uploader(
    "画像またはPDFを選択してください（複数選択可）",
    type=["jpg", "jpeg", "png", "pdf"],
    accept_multiple_files=True
)

if uploaded_files:
    st.info(f"{len(uploaded_files)} 件のファイルが選択されています。")

if st.button("PDFを作成", disabled=not uploaded_files):
    with st.spinner("PDFを作成中..."):
        files_to_send = [
            ("files", (f.name, f.getvalue(), f.type))
            for f in uploaded_files
        ]
        res = requests.post(f"{BACKEND_URL}/api/convert/images-to-pdf", files=files_to_send)

        if res.status_code == 200:
            st.success("PDFの作成が完了しました！")
            st.download_button(
                label="PDFをダウンロード",
                data=res.content,
                file_name="compiled.pdf",
                mime="application/pdf"
            )
        else:
            st.error(f"変換エラー: {res.text}")
