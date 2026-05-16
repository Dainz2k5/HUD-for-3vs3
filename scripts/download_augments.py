import os
import re
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

def download_raw_file(task):
    """Tải một file từ URL và lưu vào đường dẫn chỉ định."""
    url, save_path = task
    if os.path.exists(save_path):
        return True, "skipped"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()  # Báo lỗi nếu status code không phải 2xx
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return True, "downloaded"
    except requests.RequestException as e:
        print(f"\n[!] Lỗi khi tải {url}: {e}")
        return False, str(e)

def scrape_and_download_augments():
    """
    Cào dữ liệu ảnh Lõi Nâng Cấp trực tiếp từ trang web Community Dragon
    sử dụng BeautifulSoup để phân tích HTML một cách đáng tin cậy.
    """
    print("🔎 Đang cào dữ liệu Lõi Nâng Cấp từ Community Dragon...")
    
    # Xác định đường dẫn tuyệt đối để script chạy đúng từ bất kỳ đâu.
    # __file__ là đường dẫn đến file script hiện tại (download_augments.py)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    aug_dir = os.path.join(project_root, "app", "static", "Augments")
    os.makedirs(aug_dir, exist_ok=True)
    
    # ĐÂY LÀ THƯ MỤC CHỨA ẢNH RAW CỦA CHẾ ĐỘ VÕ ĐÀI (CHERRY)
    base_url = "https://raw.communitydragon.org/16.10/game/assets/ux/cherry/augments/icons/"
    
    try:
        response = requests.get(base_url)
        response.raise_for_status()

        try:
            # Ưu tiên dùng lxml vì tốc độ nhanh hơn. Cài đặt bằng: pip install lxml
            soup = BeautifulSoup(response.text, 'lxml')
        except Exception:
            # Nếu lxml chưa được cài, dùng parser mặc định của Python (chậm hơn)
            print("⚠️  Cảnh báo: Không tìm thấy parser 'lxml', chuyển sang 'html.parser'. Để tăng tốc, hãy cài đặt bằng: pip install lxml")
            soup = BeautifulSoup(response.text, 'html.parser')
        # Tìm tất cả các thẻ 'a' có href kết thúc bằng '.png'
        png_links = [a['href'] for a in soup.find_all('a') if a.get('href', '').endswith('.png')]

        if not png_links:
            print("❌ Không đọc được thư mục gốc! Web Community Dragon có thể đang bảo trì.")
            return

        tasks = []
        for file_name in png_links:
            full_url = base_url + file_name
            tasks.append((full_url, os.path.join(aug_dir, file_name)))
            
        print(f"🎯 Đã khóa cổ {len(tasks)} file Lõi bằng vũ lực. Đang tải...")
        
        success = 0
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(download_raw_file, task): task for task in tasks}
            for future in as_completed(futures):
                if future.result()[0]: success += 1
                
        print(f"\n✅ Tải thành công: {success}/{len(tasks)} ảnh Nâng Cấp.")
        print(f"📁 Thư mục: {aug_dir}")
        
    except Exception as e:
        print(f"Lỗi hệ thống: {e}")

if __name__ == "__main__":
    scrape_and_download_augments()