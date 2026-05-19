import os
import requests
import urllib3
import time
import json

# Tắt cảnh báo SSL vì LCU sử dụng chứng chỉ tự ký (self-signed certificate)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Thêm thư mục gốc vào sys.path để có thể import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

def get_lcu_credentials():
    """
    Đọc file lockfile để lấy port và mật khẩu kết nối với LCU API.
    """
    lockfile_path = os.path.join(config.LOL_CLIENT_PATH, "lockfile")
    try:
        with open(lockfile_path, 'r') as f:
            # Format của lockfile: process_name:PID:port:password:protocol
            data = f.read().split(':')
            return data[2], data[3] # Trả về port và password
    except FileNotFoundError:
        print("Không tìm thấy Client LMHT đang chạy. Hãy mở game lên trước.")
        return None, None

def get_champ_select_session(port, password):
    """
    Gọi LCU API để lấy dữ liệu Cấm/Chọn hiện tại.
    """
    url = f"https://127.0.0.1:{port}/lol-champ-select/v1/session"
    try:
        # User mặc định luôn là 'riot'
        response = requests.get(url, auth=('riot', password), verify=False)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            # Code 404 nghĩa là không ở trong phòng Cấm/Chọn
            return None
    except Exception as e:
        print(f"Lỗi kết nối: {e}")
        return None

def main():
    port, password = get_lcu_credentials()
    if not port or not password:
        return

    print(f"Đã kết nối với LCU ở Port: {port}. Đang chờ vào phòng Cấm/Chọn...")

    while True:
        session = get_champ_select_session(port, password)
        
        if session:
            os.system('cls' if os.name == 'nt' else 'clear') # Xóa terminal cho dễ nhìn
            print("--- ĐANG TRONG PHÒNG CẤM/CHỌN ---")
            
            # Lấy danh sách ID tướng bị cấm
            bans = session.get('bans', {})
            my_team_bans = bans.get('myTeamBans', [])
            enemy_team_bans = bans.get('theirTeamBans', [])
            
            print(f"Đội của bạn cấm (ID tướng): {my_team_bans}")
            print(f"Đội địch cấm (ID tướng): {enemy_team_bans}")
            
            # Bạn có thể trích xuất thêm dữ liệu picks từ mảng 'myTeam' và 'theirTeam'
            # Ví dụ: 
            # for player in session.get('myTeam', []):
            #     print(f"Người chơi {player['cellId']} đang chọn tướng ID: {player['championId']}")
                
        else:
            print("Đang chờ trận... (Không ở trong Cấm/Chọn)", end='\r')
            
        time.sleep(1) # Cập nhật dữ liệu mỗi giây

if __name__ == "__main__":
    main()