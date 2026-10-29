import streamlit as st
import requests
import os

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


@st.cache_data
def fetch_photo_capacity(backend_url: str, width_mm: float, height_mm: float, gap_mm: float):
    try:
        res = requests.get(
            f"{backend_url}/api/images/photo-grid-capacity",
            params={"width_mm": width_mm, "height_mm": height_mm, "gap_mm": gap_mm},
        )
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None


if "photo_reset_key" not in st.session_state:
    st.session_state.photo_reset_key = 0
if "photo_result" not in st.session_state:
    st.session_state.photo_result = None

col_title, col_btn = st.columns([4, 1])
with col_title:
    st.title("写真グリッド印刷")
with col_btn:
    st.write("")
    if st.button("クリア", key="photo_clear"):
        st.session_state.photo_reset_key += 1
        st.session_state.photo_result = None
        st.rerun()

st.write(
    "写真（正方形でなくてもOK）を指定サイズに縮小し、A4サイズ1枚のグリッドに"
    "できるだけ多く並べてPDFにまとめます。写真の比率は保たれ、向きは自動で最適化されます。"
)

st.header("1. レイアウト設定")
col_w, col_h, col_gap = st.columns(3)
with col_w:
    width_mm = st.number_input(
        "横の長さ（mm）",
        min_value=10.0,
        max_value=210.0,
        value=89.0,
        step=1.0,
        key=f"photo_w_{st.session_state.photo_reset_key}",
    )
with col_h:
    height_mm = st.number_input(
        "縦の長さ（mm）",
        min_value=10.0,
        max_value=297.0,
        value=127.0,
        step=1.0,
        key=f"photo_h_{st.session_state.photo_reset_key}",
    )
with col_gap:
    gap_mm = st.number_input(
        "余白（mm・切り取り用）",
        min_value=0.0,
        max_value=50.0,
        value=2.0,
        step=1.0,
        key=f"photo_gap_{st.session_state.photo_reset_key}",
    )

st.caption(
    "指定した縦横のサイズは配置枠です。写真は歪まないよう比率を保ったまま枠に収まり、"
    "枠を大きく使えるよう必要に応じて自動で回転します。"
)

capacity = fetch_photo_capacity(BACKEND_URL, width_mm, height_mm, gap_mm)
if capacity is None:
    st.error("バックエンドに接続できませんでした。最大枚数を取得できません。")
    st.stop()

max_images = capacity["max_images"]
cols = capacity["columns"]
rows = capacity["rows"]

if max_images < 1:
    st.error(
        f"指定サイズ {width_mm:g}×{height_mm:g}mm が大きすぎて、A4に1枚も配置できません。"
        "サイズを小さくしてください。"
    )
    st.stop()

orient_note = "（枠を横向きに回転して配置）" if capacity["rotated"] else ""
st.info(
    f"この設定では A4 1枚に **最大 {max_images} 枚**"
    f"（{cols}列 × {rows}行）配置できます。{orient_note}"
)

st.header("2. 画像のアップロード")
uploaded_files = st.file_uploader(
    "写真を選択してください（JPG・PNG、複数選択可）",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
    key=f"photo_files_{st.session_state.photo_reset_key}",
)

over_limit = False
if uploaded_files:
    count = len(uploaded_files)
    if count > max_images:
        over_limit = True
        st.warning(
            f"⚠️ 画像が {count} 枚選択されていますが、この設定でA4に配置できるのは"
            f"最大 {max_images} 枚です。**{count - max_images} 枚多い**ため、"
            "不要な画像を減らすか、サイズ・余白を小さくしてください。"
        )
    else:
        st.info(f"{count} / {max_images} 枚が選択されています。")

if st.button("PDFを作成", disabled=not uploaded_files or over_limit):
    st.session_state.photo_result = None
    with st.spinner("PDFを作成中..."):
        files_to_send = [
            ("files", (f.name, f.getvalue(), f.type))
            for f in uploaded_files
        ]
        res = requests.post(
            f"{BACKEND_URL}/api/images/photo-grid-to-pdf",
            files=files_to_send,
            data={
                "width_mm": str(width_mm),
                "height_mm": str(height_mm),
                "gap_mm": str(gap_mm),
            },
        )

        if res.status_code == 200:
            st.session_state.photo_result = res.content
        else:
            st.error(f"作成エラー: {res.text}")

if st.session_state.photo_result:
    st.success("PDFの作成が完了しました！")
    st.download_button(
        label="PDFをダウンロード",
        data=st.session_state.photo_result,
        file_name="photo_grid_a4.pdf",
        mime="application/pdf",
    )
