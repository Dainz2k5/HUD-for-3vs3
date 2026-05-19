import time
import os
import re
import sys

# Thêm thư mục gốc vào sys.path để có thể import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

def find_latest_log_file(log_directory):
    """Tìm file log mới nhất trong thư mục log của game."""
    try:
        # Tìm các file log dạng "YYYY-MM-DDTHH-MM-SS.log"
        files = [os.path.join(log_directory, f) for f in os.listdir(log_directory) if re.match(r"\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.log", f)]
        if not files:
            return None
        # Sắp xếp file theo thời gian chỉnh sửa để lấy file mới nhất
        return max(files, key=os.path.getmtime)
    except FileNotFoundError:
        print(f"[-] Lỗi: Không tìm thấy thư mục log tại '{log_directory}'.")
        print("[-] Vui lòng kiểm tra lại biến LOL_LOG_PATH ở đầu file.")
        return None

def follow(the_file):
    """Theo dõi và yield các dòng mới được thêm vào file."""
    the_file.seek(0, 2)  # Đi đến cuối file
    while True:
        line = the_file.readline()
        if not line:
            time.sleep(0.1)  # Đợi một chút nếu không có dòng mới, tránh tốn CPU
            continue
        yield line

def main():
    """
    Hàm chính, chạy một vòng lặp vô tận để:
    1. Tìm file log của trận đấu mới nhất.
    2. Nếu có trận đấu mới, bắt đầu theo dõi file log đó.
    3. In ra TẤT CẢ các dòng log mới được ghi để phân tích.
    """
    last_log_file = None
    print("--- Bắt đầu chương trình theo dõi Log Game ---")
    print(f"Thư mục Log đang được giám sát: {config.LOL_LOG_PATH}")
    print("Đang chờ trận đấu bắt đầu...")

    try:
        while True:
            current_log_file = find_latest_log_file(config.LOL_LOG_PATH)

            # Nếu không có file log (chưa vào trận), đợi và thử lại
            if not current_log_file:
                print("Không tìm thấy file log. Vui lòng vào trận đấu...", end='\r')
                time.sleep(5)
                continue

            # Nếu phát hiện một file log mới (trận đấu mới)
            if current_log_file != last_log_file:
                print("\n" + "="*60)
                print(f"[+] Phát hiện trận đấu mới! Đang theo dõi file: {os.path.basename(current_log_file)}")
                print("="*60)
                last_log_file = current_log_file
                try:
                    with open(current_log_file, 'r', encoding='utf-8', errors='ignore') as logfile:
                        log_lines = follow(logfile) # Vòng lặp này sẽ chạy vô tận
                        for line in log_lines:
                            line = line.strip()
                            # In ra TOÀN BỘ dòng log mới để bạn quan sát
                            print(line)

                            # =================================================================
                            # == PHẦN DÀNH CHO BẠN: VIẾT REGEX TẠI ĐÂY ==
                            #
                            # Nhiệm vụ: Thay thế biểu thức trong `re.search(r'...')` bên dưới.
                            # Mục tiêu:
                            #   - Nhóm 1 (`match.group(1)`) phải là Tên Người Chơi.
                            #   - Nhóm 2 (`match.group(2)`) phải là Tên Lõi Nâng Cấp.
                            #
                            # Ví dụ: Nếu dòng log là '... Player "Tên" received augment "Tên Lõi" ...'
                            # Regex sẽ là: r'Player "([^"]+)" received augment "([^"]+)"'
                            # =================================================================
                            match = re.search(r'Player "([^"]+)" received augment "([^"]+)"', line)
                            if match:
                                player_name = match.group(1)
                                augment_name = match.group(2)
                                print(f"    ==> [ĐÃ BẮT DỮ LIỆU!] Người chơi: '{player_name}', Lõi: '{augment_name}'")

                except Exception as e:
                    print(f"\n[!] Lỗi khi đọc file (có thể trận đấu đã kết thúc): {e}")
                    last_log_file = None # Đặt lại để tìm trận mới
                    print("...Sẽ thử lại hoặc chờ trận đấu mới.")
            
            time.sleep(5) # Đợi 5 giây trước khi kiểm tra lại

    except KeyboardInterrupt:
        print("\n--- Đã dừng chương trình theo dõi. ---")
    except Exception as e:
        print(f"\n[!!!] Lỗi nghiêm trọng không mong muốn: {e}")

if __name__ == "__main__":
    main()