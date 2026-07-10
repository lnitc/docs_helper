import streamlit as st

st.set_page_config(page_title="ドキュメント処理システム", layout="wide")

st.title("ドキュメント処理システム")
st.write("ドキュメントの OCR 抽出・翻訳・PDF 結合を行うツールです。")

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🔍 OCR & 翻訳")
    st.write(
        "画像・PDFからテキストを**抽出**し、内容を**手動で確認・修正**しながら翻訳します。"
        "結果はプレーンテキストです。手書き・印刷文字に対応し、スキャンPDFも自動でOCR処理します。"
    )
    st.markdown("""
- 画像（JPG・PNG）またはPDFをアップロード
- 言語ペアを選択（Cloud Translation が対応する任意の言語）
- Google Cloud Vision APIでテキスト抽出
- デジタルPDFは高速モード、スキャンPDFはOCRモードで自動切替
- **抽出テキストの手動編集が可能**
- 翻訳結果をテキストファイル（.txt）でダウンロード
""")

with col2:
    st.subheader("📄 ドキュメント翻訳（レイアウト保持）")
    st.write(
        "Word・PowerPoint・Excel・PDFファイルを、**元のレイアウトや書式を保ったまま丸ごと翻訳**します。"
        "テキストの抽出や手動編集は不要です。"
    )
    st.markdown("""
- Word（doc/docx）・PowerPoint（ppt/pptx）・Excel（xls/xlsx）・PDFに対応
- Google Cloud Document Translation APIでドキュメント全体を翻訳
- **レイアウト・書式を維持したまま**翻訳（手動編集ウィンドウなし）
- 出力形式はアップロード時と同じ形式（ファイルサイズ20MBまで）
- 翻訳済みドキュメントをそのままダウンロード
""")

with col3:
    st.subheader("📎 PDFコンパイラ")
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
st.info(
    "💡 **「OCR & 翻訳」と「ドキュメント翻訳」の使い分け**\n\n"
    "- 画像やスキャンPDFからテキストを取り出し、内容を手動で確認・修正しながら翻訳したい → **OCR & 翻訳**\n"
    "- Word・PowerPoint・Excel・PDFを、レイアウトや書式そのままで丸ごと翻訳したい（手動編集不要） → **ドキュメント翻訳（レイアウト保持）**"
)
st.info("左のサイドバーからページを選択してください。")
