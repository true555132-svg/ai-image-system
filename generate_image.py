import os
import io
import base64
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs", "images")


def _save(img_bytes: bytes, brand_key: str, product_key: str, use_case_key: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S%f")
    filename = f"{brand_key}_{product_key}_{use_case_key}_{ts}.png"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(img_bytes)
    return filepath, filename


def _to_square_png(image_path: str, size: int = 1024) -> bytes:
    """把參考圖轉成正方形 RGBA PNG（images.edit 需要）。"""
    img = Image.open(image_path).convert("RGBA")
    s = max(img.size)
    canvas = Image.new("RGBA", (s, s), (255, 255, 255, 255))
    canvas.paste(img, ((s - img.width) // 2, (s - img.height) // 2))
    canvas = canvas.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


def generate_from_reference(reference_path: str, angle: str,
                             brand_key: str, product_key: str, use_case_key: str,
                             extra_notes: str = "") -> dict:
    """用參考圖 + images.edit，模擬攝影棚多角度實拍。"""
    png_bytes = _to_square_png(reference_path)

    prompt = (
        "這是一張電商商品棚拍照片。請模擬同一個商品在攝影棚中從不同角度重新拍攝的效果。\n\n"
        "【絕對不得改變】\n"
        "商品的物理結構、濾紙摺疊數量與間距、外框形狀與比例、所有零件的相對位置、"
        "材質紋理、顏色深淺、黑色與白色區域的分布。\n"
        "商品的高度與直徑比例必須與參考圖完全一致，不得拉高、壓扁或改變長寬比。\n\n"
        "【鏡頭與透視規範 - 嚴格執行】\n"
        "使用長焦鏡頭（200mm 等效）模擬正交投影效果。\n"
        "圓柱體商品的左右兩側邊緣必須完全平行垂直，不得出現上寬下窄或上窄下寬的透視收縮。\n"
        "禁止廣角變形、桶形畸變、透視變形。商品邊緣不得彎曲或傾斜。\n\n"
        "【允許改變】\n"
        f"拍攝角度改為：{angle}。可調整光線方向與強度、陰影位置與柔和度。\n\n"
        "背景：純白無縫背景。打光：專業商品攝影棚柔光箱。商品置中。\n"
        "目標：模擬攝影棚實拍，不是生成新商品，不做任何創意詮釋。"
    )
    if extra_notes:
        prompt += f"\n補充需求：{extra_notes}"

    response = client.images.edit(
        model="gpt-image-2",
        image=("reference.png", io.BytesIO(png_bytes), "image/png"),
        prompt=prompt,
        size="1024x1024",
        n=1,
    )

    item = response.data[0]
    if getattr(item, "b64_json", None):
        img_bytes = base64.b64decode(item.b64_json)
    else:
        import requests
        img_bytes = requests.get(item.url, timeout=30).content

    filepath, filename = _save(img_bytes, brand_key, product_key, use_case_key)
    return {"filepath": filepath, "filename": filename, "angle": angle}


def generate_all_angles_from_reference(reference_path: str,
                                        brand_key: str, product_key: str, use_case_key: str,
                                        extra_notes: str = "") -> list:
    """平行生成所有角度（保留參考圖結構）。"""
    from generate_prompt import PRODUCT_OPTIONS
    angles = PRODUCT_OPTIONS[product_key]["angles"]

    def _gen(i):
        r = generate_from_reference(reference_path, angles[i],
                                     brand_key, product_key, use_case_key, extra_notes)
        r["index"] = i
        return r

    results = [None] * len(angles)
    with ThreadPoolExecutor(max_workers=len(angles)) as executor:
        futures = {executor.submit(_gen, i): i for i in range(len(angles))}
        for future in as_completed(futures):
            r = future.result()
            results[r["index"]] = r
    return results


def generate_image(prompt: str, use_case_key: str, brand_key: str, product_key: str) -> dict:
    """純文字 prompt 生成（無參考圖時使用）。"""
    response = client.images.generate(
        model="gpt-image-2",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    item = response.data[0]
    if getattr(item, "b64_json", None):
        img_bytes = base64.b64decode(item.b64_json)
    else:
        import requests
        img_bytes = requests.get(item.url, timeout=30).content

    filepath, filename = _save(img_bytes, brand_key, product_key, use_case_key)
    return {"filepath": filepath, "filename": filename}
