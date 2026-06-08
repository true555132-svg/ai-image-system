import streamlit as st
import os
from generate_prompt import (
    BRAND_CONFIG, PRODUCT_OPTIONS, USE_CASE_OPTIONS,
    analyze_reference_image, generate_prompt, save_prompt
)
from generate_image import (
    generate_image, generate_all_angles_from_reference
)

st.set_page_config(page_title="商品圖片生成器", page_icon="🖼️", layout="wide")

st.markdown("""
<style>
* { box-sizing: border-box; }
body { font-family: -apple-system, 'Noto Sans TC', sans-serif; }
.block-container { padding: 1.5rem 2rem; max-width: 1100px; }
h1 { font-size: 1.4rem; font-weight: 700; margin-bottom: 0.2rem; }
.sub { font-size: 0.85rem; color: #888; margin-bottom: 1.5rem; }
.section { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 1.2rem 1.4rem; margin-bottom: 1rem; }
.sec-title { font-size: 0.72rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: #6b7280; margin-bottom: 0.8rem; }
.result-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.result-card { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; text-align: center; }
.result-card img { width: 100%; border-radius: 6px; }
.angle-label { font-size: 0.75rem; color: #6b7280; margin: 6px 0 8px; }
.stButton > button { border-radius: 8px; font-weight: 600; }
div[data-testid="stFileUploader"] { border: 2px dashed #d1d5db; border-radius: 8px; padding: 0.8rem; background: #fafafa; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 🖼️ 商品圖片生成器")
st.markdown('<div class="sub">上傳商品參考圖 → AI 保留結構顏色 → 生成多角度白底素材</div>', unsafe_allow_html=True)

left, right = st.columns([1, 1.2], gap="large")

with left:
    # 設定
    st.markdown('<div class="section"><div class="sec-title">基本設定</div>', unsafe_allow_html=True)
    brand_map = {v["name"]: k for k, v in BRAND_CONFIG.items()}
    brand_key = brand_map[st.selectbox("品牌", list(brand_map.keys()))]

    product_map = {v["label"]: k for k, v in PRODUCT_OPTIONS.items()}
    product_key = product_map[st.selectbox("商品類型", list(product_map.keys()))]

    use_map = {v["label"]: k for k, v in USE_CASE_OPTIONS.items()}
    use_case_key = use_map[st.selectbox("圖片用途", list(use_map.keys()))]
    st.markdown('</div>', unsafe_allow_html=True)

    # 參考圖（主要功能）
    st.markdown('<div class="section"><div class="sec-title">📷 上傳商品參考圖（必填）</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("支援 JPG、PNG、WEBP",
                                type=["jpg", "jpeg", "png", "webp"],
                                label_visibility="collapsed")
    ref_path = None
    if uploaded:
        ref_dir = os.path.join(os.path.dirname(__file__), "references", "temp")
        os.makedirs(ref_dir, exist_ok=True)
        ref_path = os.path.join(ref_dir, uploaded.name)
        with open(ref_path, "wb") as f:
            f.write(uploaded.getbuffer())
        st.image(uploaded, use_container_width=True)

        if st.button("🔍 分析商品固定特徵（建議先做）", use_container_width=True):
            with st.spinner("GPT-4o 分析商品結構中..."):
                try:
                    desc = analyze_reference_image(ref_path)
                    st.session_state["ref_desc"] = desc
                except Exception as e:
                    st.error(f"分析失敗：{e}")

        if "ref_desc" in st.session_state:
            st.info(f"📋 已識別商品特徵（生成時會鎖定這些）：\n\n{st.session_state['ref_desc']}")

    st.markdown('</div>', unsafe_allow_html=True)

    # 補充說明
    extra = st.text_area("補充說明（選填）",
                         placeholder="例如：強調頂部黑色活性碳層、需顯示底部底座...",
                         height=80)

    extra_combined = extra
    if "ref_desc" in st.session_state:
        extra_combined = f"參考圖分析：{st.session_state['ref_desc']}\n{extra}".strip()

    # 按鈕
    st.markdown("---")
    if ref_path:
        if st.button("🎯 一鍵生成全部角度", type="primary", use_container_width=True):
            angles = PRODUCT_OPTIONS[product_key]["angles"]
            with st.spinner(f"平行生成 {len(angles)} 種角度，約 20-40 秒..."):
                try:
                    results = generate_all_angles_from_reference(
                        ref_path, brand_key, product_key, use_case_key, extra_combined
                    )
                    st.session_state["results"] = results
                    st.session_state.pop("single_result", None)
                except Exception as e:
                    st.error(f"生成失敗：{e}")
            st.rerun()
    else:
        st.button("🎯 一鍵生成全部角度（請先上傳參考圖）", disabled=True, use_container_width=True)

with right:
    if "results" in st.session_state:
        results = st.session_state["results"]
        st.markdown("### 生成結果")

        cols = st.columns(len(results))
        for i, r in enumerate(results):
            if r:
                with cols[i]:
                    st.image(r["filepath"], use_container_width=True)
                    st.caption(r["angle"])
                    with open(r["filepath"], "rb") as f:
                        st.download_button(
                            "⬇ 下載",
                            data=f,
                            file_name=r["filename"],
                            mime="image/png",
                            use_container_width=True,
                            key=f"dl_{i}"
                        )
    else:
        st.markdown("""
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                    height:200px;border:2px dashed #e5e7eb;border-radius:12px;background:#fafafa;">
            <div style="font-size:2rem;margin-bottom:0.5rem;">🖼️</div>
            <div style="font-size:0.9rem;font-weight:600;color:#374151;">上傳參考圖後按「一鍵生成全部角度」</div>
        </div>
        """, unsafe_allow_html=True)

    # 歷史記錄
    st.markdown("---")
    st.markdown("### 📁 歷史生成記錄")
    img_dir = os.path.join(os.path.dirname(__file__), "outputs", "images")
    if os.path.exists(img_dir):
        all_imgs = sorted(
            [f for f in os.listdir(img_dir) if f.endswith(".png")],
            reverse=True
        )
        if all_imgs:
            # 每列顯示 4 張
            cols_per_row = 4
            for row_start in range(0, min(len(all_imgs), 20), cols_per_row):
                row_imgs = all_imgs[row_start:row_start + cols_per_row]
                cols = st.columns(cols_per_row)
                for j, fname in enumerate(row_imgs):
                    fpath = os.path.join(img_dir, fname)
                    with cols[j]:
                        st.image(fpath, use_container_width=True)
                        # 從檔名取時間戳
                        parts = fname.replace(".png", "").split("_")
                        ts = "_".join(parts[-2:]) if len(parts) >= 2 else ""
                        st.caption(ts)
                        with open(fpath, "rb") as f:
                            st.download_button(
                                "⬇",
                                data=f,
                                file_name=fname,
                                mime="image/png",
                                use_container_width=True,
                                key=f"hist_{fname}"
                            )
        else:
            st.markdown('<div style="color:#9ca3af;font-size:0.85rem;">尚無記錄</div>', unsafe_allow_html=True)
