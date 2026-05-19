import os
import requests
import json
import sys

# Thêm thư mục gốc vào hệ thống để đọc file cấu hình config.py tự động
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    import config
    # Lấy đường dẫn file cấu hình từ config của bạn, ví dụ đổi tên file đích thành arena_augments_vi.json
    # Hoặc bạn có thể chỉ định cứng đường dẫn file ở dưới
    JSON_OUTPUT_PATH = getattr(config, "CD_ARENA_JSON_PATH_VI", "data/arena_augments_vi.json")
except Exception:
    JSON_OUTPUT_PATH = "data/arena_augments_vi.json"

URL_VI = "https://raw.communitydragon.org/latest/cdragon/arena/vi_vn.json"

def download_vi_data():
    print("🚀 Đang tải file dữ liệu Lõi Công Nghệ Tiếng Việt từ CommunityDragon...")
    os.makedirs(os.path.dirname(JSON_OUTPUT_PATH), exist_ok=True)
    
    try:
        response = requests.get(URL_VI, timeout=15)
        response.raise_for_status()
        raw_data = response.json()
        
        with open(JSON_OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=4)
            
        print(f"✅ Đã tải và lưu thành công file dữ liệu Tiếng Việt tại: {JSON_OUTPUT_PATH}")
    except Exception as e:
        print(f"❌ Lỗi khi tải file dữ liệu: {e}")

if __name__ == "__main__":
    download_vi_data()