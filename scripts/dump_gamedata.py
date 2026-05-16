import requests
import urllib3
import json
import time

# Tắt cảnh báo SSL vì API game sử dụng chứng chỉ tự ký
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LIVE_CLIENT_API_URL = "https://127.0.0.1:2999/liveclientdata/allgamedata"
OUTPUT_FILENAME = "live_game_data_dump.json"

def dump_live_game_data():
    """
    Kết nối đến Live Client Data API và lưu toàn bộ dữ liệu ra file JSON.
    Hữu ích cho việc debug và khám phá các trường dữ liệu có sẵn.
    """
    print("Đang thử kết nối tới Live Client Data API...")
    try:
        response = requests.get(LIVE_CLIENT_API_URL, verify=False, timeout=2)
        
        if response.status_code == 200:
            data = response.json()
            
            # Lưu dữ liệu ra một file JSON để dễ đọc và tìm kiếm
            with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                
            print(f"✅ Đã lưu toàn bộ dữ liệu thành công vào file '{OUTPUT_FILENAME}'!")
            print("   Mở file này lên và dùng Ctrl+F để tìm kiếm thông tin bạn cần.")
            
        else:
            print(f"Lỗi khi gọi API: {response.status_code} - {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ LỖI: Không thể kết nối. Hãy chắc chắn rằng bạn đang ở trong một trận đấu.")
    except Exception as e:
        print(f"❌ Lỗi không mong muốn: {e}")

if __name__ == "__main__":
    dump_live_game_data()