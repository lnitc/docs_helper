import streamlit as st
import requests
import os

# Docker環境変数からバックエンドURLを取得
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="ロシア語業務翻訳アプリ", layout="wide")
st.title("🇷🇺 ロシア語ドキュメント OCR & 翻訳システム")

# セッションステート（状態保持）の初期化
if "extracted_text" not in st.session_state:
    st.session_state.extracted_text = ""
if "translated_text" not in st.session_state:
    st.session_state.translated_text = ""

# --- Step 1: ファイルアップロード & OCR ---
st.header("1. 画像のアップロードとテキスト化 (OCR)")
uploaded_file = st.file_uploader("ロシア語の筆記体画像 (JPEG) をアップロード", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="アップロードされた画像", width=500)
    
    if st.button("OCRでテキスト抽出を実行"):
        with st.spinner("Google Cloud Vision APIで解析中..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            res = requests.post(f"{BACKEND_URL}/api/ocr/image", files=files)
            
            if res.status_code == 200:
                st.session_state.extracted_text = res.json().get("extracted_text", "")
                st.success("テキストの抽出に成功しました！")
            else:
                st.error(f"OCRエラー: {res.text}")

# --- Step 2: テキストの手動編集 ---
st.header("2. テキストの確認・手動編集")
st.info("OCRの誤認識があれば、ここで直接テキストを修正してください。")
edited_text = st.text_area("抽出されたロシア語テキスト", value=st.session_state.extracted_text, height=200)

# 編集内容を常にステートに反映
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
    
    # テキストファイルとしてダウンロード
    st.download_button(
        label="📄 翻訳結果をテキスト(txt)でダウンロード",
        data=st.session_state.translated_text,
        file_name="translated_result.txt",
        mime="text/plain"
    )