import streamlit as st

st.set_page_config(page_title="ロシア語ドキュメント処理システム", layout="wide")

st.title("ロシア語ドキュメント処理システム")
st.write("ロシア語のドキュメントを処理するための2つのツールを提供します。")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("OCR & 翻訳")
    st.write(
        "ロシア語の画像・PDFからテキストを抽出し、日本語に翻訳します。"
        "手書き・印刷文字に対応し、スキャンPDFも自動でOCR処理します。"
    )
    st.markdown("""
- 画像（JPG・PNG）またはPDFをアップロード
- Google Cloud Vision APIでテキスト抽出
- デジタルPDFは高速モード、スキャンPDFはOCRモードで自動切替
- 抽出テキストの手動編集が可能
- Google Cloud Translation APIで日本語に翻訳
- 翻訳結果をテキストファイルでダウンロード
""")

with col2:
    st.subheader("PDFコンパイラ")
    st.write(
        "複数の画像やPDFファイルを1つのPDFにまとめます。"
        "ファイルの順番通りにA4サイズのPDFとして出力します。"
    )
    st.markdown("""
- 画像（JPG・PNG）またはPDFを複数選択
- A4サイズに自動整形・中央配置
- ファイルの順番通りにページを結合
- 結合済みPDFをダウンロード
""")

st.divider()
st.info("左のサイドバーからページを選択してください。")
