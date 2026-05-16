import os
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def download_raw_file(task):
    url, save_path = task
    if os.path.exists(save_path): return True
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            with open(save_path, 'wb') as f: f.write(r.content)
            return True
    except: pass
    return False

def force_rip_arena_augments():
    print("💀 ĐANG CÀO TRỰC TIẾP VÀO THƯ MỤC GỐC CỦA MÁY CHỦ...")
    
    aug_dir = "LOL_Broadcast_Assets_Final/Nang_Cap_Vo_Dai"
    os.makedirs(aug_dir, exist_ok=True)
    
    # ĐÂY LÀ THƯ MỤC CHỨA ẢNH RAW CỦA CHẾ ĐỘ VÕ ĐÀI (CHERRY)
    url = "https://raw.communitydragon.org/latest/game/assets/ux/cherry/augments/icons/"
    
    try:
        # Tải thẳng mã nguồn HTML của trang web thư mục
        html_content = requests.get(url).text
        
        # Dùng Regex móc sạch mọi đường link có đuôi .png hiển thị trên web
        png_files = re.findall(r'href="([^"]+\.png)"', html_content)
        
        if not png_files:
            print("❌ Không đọc được thư mục gốc! Web Community Dragon có thể đang bảo trì.")
            return

        tasks = []
        for file_name in png_files:
            # File name trên đó thường có dạng "cherry_augment_stat_ap.png"
            full_url = url + file_name
            tasks.append((full_url, os.path.join(aug_dir, file_name)))
            
        print(f"🎯 Đã khóa cổ {len(tasks)} file Lõi bằng vũ lực. Đang tải...")
        
        success = 0
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(download_raw_file, task): task for task in tasks}
            for future in as_completed(futures):
                if future.result(): success += 1
                
        print(f"\n✅ CƯỚP THÀNH CÔNG: {success}/{len(tasks)} ảnh Nâng Cấp.")
        print(f"📁 Thư mục: {aug_dir}")
        
    except Exception as e:
        print(f"Lỗi hệ thống: {e}")

if __name__ == "__main__":
    force_rip_arena_augments()