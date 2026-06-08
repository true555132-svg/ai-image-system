import base64
import os
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BRAND_CONFIG = {
    "luair": {
        "name": "LuAir 濾呼吸",
        "主色調": "白色與淺天藍色",
        "style": "乾淨、專業、健康導向"
    }
}

PRODUCT_OPTIONS = {
    "hepa_filter": {
        "label": "HEPA 濾網",
        "商品名稱": "HEPA 空氣清淨濾網",
        "商品描述": "圓柱形 HEPA 空氣清淨替換濾網。外框：白色塑膠。濾材：緊密摺疊的白色 HEPA 濾紙。底層：淺灰色前置濾網。重要：精確還原真實商品顏色——只有白色和淺灰色，不得添加藍色、青色、綠色或任何裝飾色。不做色彩分級，不做藝術詮釋。",
        "angles": ["45度斜角正面", "正面直視角度（保持原商品高寬比，圓柱高度與直徑比例不變）", "輕微俯視角度"]
    },
    "carbon_filter": {
        "label": "活性碳濾網",
        "商品名稱": "活性碳濾網",
        "商品描述": "深炭黑色活性碳濾網，蜂巢或格狀結構，與白色外框形成對比。",
        "angles": ["45度斜角正面", "近景材質特寫"]
    },
    "combo_set": {
        "label": "濾網組合包",
        "商品名稱": "空氣濾網替換組合包",
        "商品描述": "多層濾網整齊排列，乾淨的組合包裝呈現，堆疊展示 HEPA 與活性碳各層。",
        "angles": ["俯視平拍排列", "輕微斜角展示各層"]
    }
}

USE_CASE_OPTIONS = {
    "shopee_main": {
        "label": "蝦皮主圖",
        "比例": "1:1",
        "extra": "正方形格式，符合蝦皮規格，商品需佔畫面 85%"
    },
    "shopline_product": {
        "label": "官網商品圖",
        "比例": "4:3 或 1:1",
        "extra": "乾淨電商商品頁圖片，SHOPLINE 適用"
    },
    "seo_blog": {
        "label": "SEO文章配圖",
        "比例": "16:9",
        "extra": "可加入生活情境，商品在使用中或乾淨居家環境"
    }
}


def analyze_reference_image(image_path: str) -> str:
    """用 GPT-4o 分析參考圖，回傳產品外觀描述（繁體中文），加入 prompt 提升一致性。"""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    ext = image_path.rsplit('.', 1)[-1].lower()
    mime = 'image/png' if ext == 'png' else 'image/jpeg'
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                {"type": "text", "text": (
                    "你是電商商品攝影師的 AI 助理。請用繁體中文精確描述這個商品的固定物理特徵，"
                    "這些描述將用來確保 AI 生成時不改變商品本身。\n"
                    "請涵蓋：外框顏色與形狀、濾材顏色與紋路、可見的摺疊數量與間距、"
                    "各部位顏色分布（例如頂部黑色、側面白色）、材質質感。\n"
                    "用條列式，每項一句，最多 5 項。"
                )}
            ]
        }],
        max_tokens=150
    )
    return resp.choices[0].message.content.strip()


def load_template():
    template_path = os.path.join(BASE_DIR, "templates", "white-background-product.txt")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


def generate_prompt(brand_key, product_key, use_case_key, angle_index=0, extra_notes=""):
    brand = BRAND_CONFIG[brand_key]
    product = PRODUCT_OPTIONS[product_key]
    use_case = USE_CASE_OPTIONS[use_case_key]
    angle = product["angles"][angle_index] if angle_index < len(product["angles"]) else product["angles"][0]

    template = load_template()

    prompt = template.replace("{{商品名稱}}", product["商品名稱"])
    prompt = prompt.replace("{{品牌名稱}}", brand["name"])
    prompt = prompt.replace("{{商品描述}}", product["商品描述"])
    prompt = prompt.replace("{{拍攝角度}}", angle)
    prompt = prompt.replace("{{主色調}}", brand["主色調"])
    prompt = prompt.replace("比例：1:1（正方形，蝦皮主圖標準）",
                            f"比例：{use_case['比例']}")

    if use_case.get("extra"):
        prompt += f"\n\n額外要求：\n{use_case['extra']}"

    if extra_notes:
        prompt += f"\n\n補充說明：\n{extra_notes}"

    return prompt


def save_prompt(prompt, brand_key, product_key, use_case_key):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{brand_key}_{product_key}_{use_case_key}_{timestamp}.txt"
    output_dir = os.path.join(BASE_DIR, "outputs", "prompts")
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"品牌：{BRAND_CONFIG[brand_key]['name']}\n")
        f.write(f"商品：{PRODUCT_OPTIONS[product_key]['label']}\n")
        f.write(f"用途：{USE_CASE_OPTIONS[use_case_key]['label']}\n")
        f.write(f"生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(prompt)
    return filepath
