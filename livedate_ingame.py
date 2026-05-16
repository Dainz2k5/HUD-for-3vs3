import requests
import urllib3
import time
import os

# Tắt cảnh báo chứng chỉ SSL cục bộ
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Endpoint tổng hợp toàn bộ dữ liệu trận đấu hiện tại
LIVE_API_URL = "https://127.0.0.1:2999/liveclientdata/allgamedata"

def get_live_game_data():
    try:
        # Gọi API lấy dữ liệu, verify=False vì Riot dùng chứng chỉ tự ký
        response = requests.get(LIVE_API_URL, verify=False)
        
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.ConnectionError:
        # Lỗi này xuất hiện khi bạn chưa vào trận đấu
        return None
    return None

def main():
    print("Đang chờ trận đấu bắt đầu...")
    
    while True:
        data = get_live_game_data()
        
        if data:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("--- ĐANG TRONG TRẬN ĐẤU ---")
            
            # Thời gian trận đấu
            game_time = int(data.get("gameData", {}).get("gameTime", 0))
            minutes, seconds = divmod(game_time, 60)
            print(f"Thời gian: {minutes:02d}:{seconds:02d}")
            
            # Thông tin người chơi (Active Player)
            active_player = data.get("activePlayer", {})
            name = active_player.get("summonerName", "Unknown")
            stats = active_player.get("championStats", {})
            
            print(f"\nNgười chơi: {name}")
            print(f"Máu: {stats.get('currentHealth')} / {stats.get('maxHealth')}")
            print(f"Vàng hiện tại: {active_player.get('currentGold')}")
            
            # Các sự kiện gần nhất (Kills, Rồng, Trụ...)
            events = data.get("events", {}).get("Events", [])
            if events:
                latest_event = events[-1]
                print(f"\nSự kiện mới nhất: {latest_event.get('EventName')} tại phút {int(latest_event.get('EventTime', 0)//60)}")
                
        else:
            print("Chưa kết nối được. Vui lòng vào trận đấu...", end='\r')
            
        # Cập nhật dữ liệu mỗi 0.5 giây
        time.sleep(0.5)

if __name__ == "__main__":
    main()