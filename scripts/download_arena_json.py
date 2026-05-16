import requests
import os
import sys

# Thêm thư mục gốc vào sys.path để có thể import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

URL = "https://raw.communitydragon.org/latest/cdragon/arena/en_us.json"
OUTPUT_PATH = config.CD_ARENA_JSON_PATH

def download_arena_json():
    """
    Tải file arena_augments.json từ Community Dragon và lưu vào thư mục gốc.
    """
    print(f"Đang tải file định nghĩa Lõi từ: {URL}")
    try:
        response = requests.get(URL, timeout=15)
        response.raise_for_status()  # Báo lỗi nếu status code không phải 200
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"✅ Tải thành công! Đã lưu file vào: {OUTPUT_PATH}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi khi tải file: {e}")

if __name__ == "__main__":
    download_arena_json()
