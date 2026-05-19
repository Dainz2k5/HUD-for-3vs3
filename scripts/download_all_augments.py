import os
import requests
import sys
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CẬP NHẬT ĐƯỜNG DẪN ĐỘNG ---
# Thêm thư mục gốc vào hệ thống để đọc file cấu hình config.py tự động
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

BASE_URL = "https://raw.communitydragon.org/latest/game/assets/ux/cherry/augments/"
# Tự động lấy đường dẫn thư mục static/Augments dựa theo file cấu hình tổng
TARGET_DIR = config.AUGMENT_ICON_DIR

# Danh sách chứa tất cả các tác vụ tải file dưới dạng: (url_tải, đường_dẫn_lưu_máy)
download_tasks = []

def extract_files_and_folders_recursive(current_url, current_local_dir):
    """
    Hàm đệ quy quét qua toàn bộ cấu trúc cây thư mục trực tuyến
    và chuẩn bị danh sách file cần tải.
    """
    print(f"📁 Đang quét thư mục: {current_url}")
    try:
        response = requests.get(current_url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Tìm tất cả các thẻ liên kết 'a' trong trang danh mục của Apache/Nginx
        for a in soup.find_all('a'):
            href = a.get('href', '')
            
            # Bỏ qua các liên kết hệ thống hoặc quay lại thư mục cha
            if not href or href in ['../', './', '/'] or href.startswith('?'):
                continue
                
            # Giải mã các ký tự đặc biệt trên URL (Ví dụ: %20 thành dấu cách)
            clean_href = unquote(href)
            full_child_url = urljoin(current_url, href)
            
            # KIỂM TRA NẾU LÀ THƯ MỤC CON (kết thúc bằng dấu /)
            if href.endswith('/'):
                # Tạo đường dẫn thư mục mới tương ứng dưới máy tính
                new_local_dir = os.path.join(current_local_dir, clean_href.strip('/'))
                os.makedirs(new_local_dir, exist_ok=True)
                
                # Gọi đệ quy để chui vào bên trong thư mục con này quét tiếp
                extract_files_and_folders_recursive(full_child_url, new_local_dir)
            else:
                # 🛠️ BỘ LỌC CHÍ MẠNG: Tách lấy phần tên file và phần mở rộng (đuôi file) để kiểm tra
                filename_lower = clean_href.lower()
                base_name, _ = os.path.splitext(filename_lower)
                
                # Nếu tên file kết thúc bằng "_small", bỏ qua lập tức, không đưa vào download_tasks
                if base_name.endswith('_small'):
                    continue
                
                # NẾU LÀ FILE CHUẨN (LARGE/NORMAL): Đưa vào danh sách chờ tải
                file_save_path = os.path.join(current_local_dir, clean_href)
                download_tasks.append((full_child_url, file_save_path))
                
    except Exception as e:
        print(f"❌ Lỗi khi quét cấu trúc tại {current_url}: {e}")

def download_single_file(task):
    """Hàm xử lý tải một file đơn lẻ và ghi vào ổ cứng."""
    url, save_path = task
    
    # Nếu file đã tồn tại hoàn chỉnh dưới máy thì bỏ qua để tiết kiệm băng thông
    if os.path.exists(save_path):
        return True, "skipped"
        
    try:
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(res.content)
        return True, "downloaded"
    except Exception as e:
        return False, str(e)

def main():
    print("🚀 BẮT ĐẦU QUY TRÌNH QUÉT TOÀN BỘ THƯ MỤC CHERRY AUGMENTS (ĐÃ KÍCH HOẠT BỘ LỌC CHỐNG TẢI FILE SMALL)...")
    
    # Tạo thư mục gốc nếu chưa có
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    # Bước 1: Quét toàn bộ hệ thống thư mục (Tìm file và tự tạo cấu trúc folder con)
    extract_files_and_folders_recursive(BASE_URL, TARGET_DIR)
    
    total_files = len(download_tasks)
    print(f"\n🎯 Quét hoàn tất! Phát hiện tổng cộng {total_files} file chất lượng cao (Large/Normal) cần tải.")
    
    if total_files == 0:
        print("Không tìm thấy file nào hoặc máy chủ đang chặn kết nối.")
        return

    # Bước 2: Kích hoạt tải đa luồng tốc độ cao cho danh sách file đã thu thập
    print("⚡ Đang tải xuống dữ liệu bằng hệ thống đa luồng...")
    success_count = 0
    skipped_count = 0
    
    # Sử dụng tối đa 20 luồng (max_workers=20) chạy song song
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(download_single_file, task): task for task in download_tasks}
        
        for index, future in enumerate(as_completed(futures), 1):
            success, status = future.result()
            if success:
                success_count += 1
                if status == "skipped":
                    skipped_count += 1
            
            # In tiến độ tải theo thời gian thực lên màn hình
            print(f"\rTiến độ: [{index}/{total_files}] - Đã tải thành công: {success_count}", end="", flush=True)

    print("\n\n=== 🎉 HOÀN THÀNH QUY TRÌNH ===")
    print(f"✅ Tổng số file tải mới/cập nhật: {success_count - skipped_count}")
    print(f"♻️ Số file cũ đã có sẵn (bỏ qua): {skipped_count}")
    print(f"📁 Toàn bộ cấu trúc folder đã được lưu tại: {TARGET_DIR}")

if __name__ == "__main__":
    main()