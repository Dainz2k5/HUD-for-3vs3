import requests
import urllib3
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def dump_all_game_data():
    # Endpoint này lấy TOÀN BỘ mọi thông tin API có thể cung cấp
    url = "https://127.0.0.1:2999/liveclientdata/allgamedata"
    
    try:
        response = requests.get(url, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            
            # Lưu dữ liệu ra một file JSON để dễ đọc và tìm kiếm
            with open("arena_data_dump.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                
            print("Đã lưu toàn bộ dữ liệu thành công vào file 'arena_data_dump.json'!")
            print("Hãy mở file này lên và dùng Ctrl+F để tìm tên Lõi nâng cấp.")
            
        else:
            print(f"Lỗi: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("LỖI: Không tìm thấy máy chủ game. Hãy chắc chắn bạn đang ở trong trận.")
    except Exception as e:
        print(f"Lỗi không xác định: {e}")

if __name__ == "__main__":
    dump_all_game_data()