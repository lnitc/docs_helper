import streamlit as st
import requests
import os

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


@st.cache_data
def fetch_capacity(backend_url: str, size_mm: float, gap_mm: float):
    try:
        res = requests.get(
            f"{backend_url}/api/images/grid-capacity",
            params={"size_mm": size_mm, "gap_mm": gap_mm},
        )
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None


if "grid_reset_key" not in st.session_state:
    st.session_state.grid_reset_key = 0
if "grid_result" not in st.session_state:
    st.session_state.grid_result = None

col_title, col_btn = st.columns([4, 1])
with col_title:
    st.title("画像グリッド印刷")
with col_btn:
    st.write("")
    if st.button("クリア", key="grid_clear"):
        st.session_state.grid_reset_key += 1
        st.session_state.grid_result = None
        st.rerun()

st.write(
    "正方形の画像を指定サイズに縮小し、A4サイズ1枚のグリッドに並べてPDFにまとめます。"
    "コンビニ印刷して切り抜く、ジャンクジャーナリング用途に便利です。"
)

st.header("1. レイアウト設定")
col_size, col_gap = st.columns(2)
with col_size:
    size_mm = st.number_input(
        "画像サイズ（mm・正方形の1辺）",
        min_value=10.0,
        max_value=200.0,
        value=58.0,
        step=1.0,
        key=f"grid_size_{st.session_state.grid_reset_key}",
    )
with col_gap:
    gap_mm = st.number_input(
        "画像同士の余白（mm・切り取り用）",
        min_value=0.0,
        max_value=50.0,
        value=2.0,
        step=1.0,
        key=f"grid_gap_{st.session_state.grid_reset_key}",
    )

capacity = fetch_capacity(BACKEND_URL, size_mm, gap_mm)
if capacity is None:
    st.error("バックエンドに接続できませんでした。最大枚数を取得できません。")
    st.stop()

max_images = capacity["max_images"]
cols = capacity["columns"]
rows = capacity["rows"]

if max_images < 1:
    st.error(
        f"画像サイズ {size_mm:g}mm が大きすぎて、A4に1枚も配置できません。"
        "サイズを小さくしてください。"
    )
    st.stop()

st.info(
    f"この設定では A4 1枚に **最大 {max_images} 枚**（{cols}列 × {rows}行）配置できます。"
)

st.header("2. 画像のアップロード")
uploaded_files = st.file_uploader(
    "正方形の画像を選択してください（JPG・PNG、複数選択可）",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
    key=f"grid_files_{st.session_state.grid_reset_key}",
)

over_limit = False
if uploaded_files:
    count = len(uploaded_files)
    if count > max_images:
        over_limit = True
        st.warning(
            f"⚠️ 画像が {count} 枚選択されていますが、この設定でA4に配置できるのは"
            f"最大 {max_images} 枚です。**{count - max_images} 枚多い**ため、"
            "不要な画像を減らすか、画像サイズ・余白を小さくしてください。"
        )
    else:
        st.info(f"{count} / {max_images} 枚が選択されています。")

if st.button("PDFを作成", disabled=not uploaded_files or over_limit):
    st.session_state.grid_result = None
    with st.spinner("PDFを作成中..."):
        files_to_send = [
            ("files", (f.name, f.getvalue(), f.type))
            for f in uploaded_files
        ]
        res = requests.post(
            f"{BACKEND_URL}/api/images/grid-to-pdf",
            files=files_to_send,
            data={"size_mm": str(size_mm), "gap_mm": str(gap_mm)},
        )

        if res.status_code == 200:
            st.session_state.grid_result = res.content
        else:
            st.error(f"作成エラー: {res.text}")

if st.session_state.grid_result:
    st.success("PDFの作成が完了しました！")
    st.download_button(
        label="PDFをダウンロード",
        data=st.session_state.grid_result,
        file_name="image_grid_a4.pdf",
        mime="application/pdf",
    )
