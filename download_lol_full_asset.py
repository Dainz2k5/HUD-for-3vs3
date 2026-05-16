import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==========================================
# 1. CÁC HÀM TIỆN ÍCH CƠ BẢN
# ==========================================

def get_latest_version():
    url = "https://ddragon.leagueoflegends.com/api/versions.json"
    return requests.get(url).json()[0]

def sanitize_filename(filename):
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    return filename.strip()

def download_file(task):
    url, save_path = task
    # Nếu file đã tồn tại, bỏ qua để tiết kiệm thời gian chạy lại
    if os.path.exists(save_path):
        return None 
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        return False
    except Exception:
        return False

# ==========================================
# 2. HỆ THỐNG QUÉT VÀ PHÂN LOẠI DỮ LIỆU
# ==========================================

def gather_champion_tasks(version, base_dir):
    """Gom Tướng: Icon, Ảnh Full (Mặc định), Âm thanh (Cấm/Chọn), Kỹ năng."""
    tasks = []
    champions = requests.get(f"http://ddragon.leagueoflegends.com/cdn/{version}/data/vi_VN/champion.json").json()['data']

    # Tạo thư mục
    icon_dir = os.path.join(base_dir, "Champion_Icons")
    full_dir = os.path.join(base_dir, "Champion_Full_Images")
    audio_dir = os.path.join(base_dir, "Audio")
    ability_dir = os.path.join(base_dir, "Champion_Abilities")
    
    for d in [icon_dir, full_dir, audio_dir, ability_dir]: 
        os.makedirs(d, exist_ok=True)

    for champ_id, champ_data in champions.items():
        champ_name = sanitize_filename(champ_data['name'])
        champ_num_id = champ_data['key']  # BẮT BUỘC DÙNG ID SỐ CHO AUDIO

        # 1. Âm thanh Cấm / Chọn (Đã sửa chuẩn link Riot)
        pick_audio = f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/vi_vn/v1/champion-choose/{champ_num_id}.ogg"
        ban_audio = f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/vi_vn/v1/champion-ban/{champ_num_id}.ogg"
        tasks.extend([
            (pick_audio, os.path.join(audio_dir, f"{champ_name}_Pick.ogg")),
            (ban_audio, os.path.join(audio_dir, f"{champ_name}_Ban.ogg"))
        ])

        # 2. Ảnh Tướng Mặc Định (Chỉ lấy _0)
        splash_url = f"http://ddragon.leagueoflegends.com/cdn/img/champion/splash/{champ_id}_0.jpg"
        loading_url = f"http://ddragon.leagueoflegends.com/cdn/img/champion/loading/{champ_id}_0.jpg"
        square_url = f"http://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{champ_id}.png"
        
        tasks.extend([
            (splash_url, os.path.join(full_dir, f"{champ_name}_Splash.jpg")),
            (loading_url, os.path.join(full_dir, f"{champ_name}_Loading.jpg")),
            (square_url, os.path.join(icon_dir, f"{champ_name}_Icon.png"))
        ])

        # 3. Kỹ năng & Nội tại
        try:
            detail = requests.get(f"http://ddragon.leagueoflegends.com/cdn/{version}/data/vi_VN/champion/{champ_id}.json").json()['data'][champ_id]
            
            passive_img = detail['passive']['image']['full']
            tasks.append((f"http://ddragon.leagueoflegends.com/cdn/{version}/img/passive/{passive_img}", os.path.join(ability_dir, f"{champ_name}_Passive.png")))
            
            spell_keys = ['Q', 'W', 'E', 'R']
            for i, spell in enumerate(detail['spells'][:4]):
                spell_img = spell['image']['full']
                tasks.append((f"http://ddragon.leagueoflegends.com/cdn/{version}/img/spell/{spell_img}", os.path.join(ability_dir, f"{champ_name}_{spell_keys[i]}.png")))
        except Exception:
            pass 
            
    return tasks

def gather_item_tasks(version, base_dir):
    """Lấy Trang bị chuẩn (Mua được bằng Vàng)."""
    tasks = []
    item_dir = os.path.join(base_dir, "Items")
    os.makedirs(item_dir, exist_ok=True)

    items = requests.get(f"http://ddragon.leagueoflegends.com/cdn/{version}/data/vi_VN/item.json").json()['data']
    for item_id, item_info in items.items():
        if item_info.get('gold', {}).get('purchasable', False):
            safe_name = sanitize_filename(item_info.get('name', ''))
            img_url = f"http://ddragon.leagueoflegends.com/cdn/{version}/img/item/{item_id}.png"
            tasks.append((img_url, os.path.join(item_dir, f"Item_{safe_name}_{item_id}.png")))
            
    return tasks

def gather_augment_tasks(base_dir):
    """Móc dữ liệu LÕI VÕ ĐÀI / ARAM trực tiếp từ file thô Community Dragon."""
    tasks = []
    aug_dir = os.path.join(base_dir, "Augments")
    os.makedirs(aug_dir, exist_ok=True)

    try:
        url = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/vi_vn/v1/items.json"
        items_data = requests.get(url).json()
        
        for item in items_data:
            icon_path = item.get("iconPath", "").lower()
            name = item.get("name", "")
            
            # Quét mã ngầm: cherry = Võ Đài, augment = Lõi
            if "cherry" in icon_path or "augment" in icon_path or "lõi" in name.lower():
                item_id = item.get("id")
                safe_name = sanitize_filename(name)
                img_url = f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/item-icons/{item_id}.png"
                tasks.append((img_url, os.path.join(aug_dir, f"Augment_{safe_name}_{item_id}.png")))
    except Exception:
        pass
        
    return tasks

def gather_misc_tasks(version, base_dir):
    """Gom Ngọc, Phép bổ trợ, Mục tiêu, UI Broadcast."""
    tasks = []
    
    # 1. Ngọc tái tổ hợp
    rune_dir = os.path.join(base_dir, "Runes")
    os.makedirs(rune_dir, exist_ok=True)
    runes = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{version}/data/vi_VN/runesReforged.json").json()
    for tree in runes:
        t_name = sanitize_filename(tree['name'])
        tasks.append((f"https://ddragon.leagueoflegends.com/cdn/img/{tree['icon']}", os.path.join(rune_dir, f"Tree_{t_name}.png")))
        for slot in tree['slots']:
            for rune in slot['runes']:
                r_name = sanitize_filename(rune['name'])
                tasks.append((f"https://ddragon.leagueoflegends.com/cdn/img/{rune['icon']}", os.path.join(rune_dir, f"Rune_{r_name}.png")))

    # 2. Phép bổ trợ
    spell_dir = os.path.join(base_dir, "Spells")
    os.makedirs(spell_dir, exist_ok=True)
    spells = requests.get(f"http://ddragon.leagueoflegends.com/cdn/{version}/data/vi_VN/summoner.json").json()['data']
    for s_id, s_info in spells.items():
        safe_name = sanitize_filename(s_info['name'])
        tasks.append((f"http://ddragon.leagueoflegends.com/cdn/{version}/img/spell/{s_id}.png", os.path.join(spell_dir, f"Spell_{safe_name}.png")))

    # 3. Mục tiêu lớn (Objectives) ĐÃ TÁCH RIÊNG FILE
    obj_dir = os.path.join(base_dir, "Objectives")
    os.makedirs(obj_dir, exist_ok=True)
    cd_base = "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-match-history/global/default"
    objs = {
        "Baron": "baron-100", "Dragon": "dragon-100", "Elder_Dragon": "elder-dragon-100", 
        "Herald": "herald-100", "Tower": "tower-100", "Inhibitor": "inhibitor-100", "Voidgrub": "hoard-100"
    }
    for name, code in objs.items():
        tasks.append((f"{cd_base}/{code}.png", os.path.join(obj_dir, f"Obj_{name}.png")))

    # 4. UI Broadcast (Bản đồ, Vị trí, Rank)
    ui_dir = os.path.join(base_dir, "Broadcast_UI")
    os.makedirs(ui_dir, exist_ok=True)
    tasks.append((f"http://ddragon.leagueoflegends.com/cdn/{version}/img/map/map11.png", os.path.join(ui_dir, "Map_SummonersRift.png")))
    
    roles = ["top", "jungle", "middle", "bottom", "utility"]
    role_url = "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-career-stats/global/default/position_{}.png"
    for r in roles: tasks.append((role_url.format(r), os.path.join(ui_dir, f"Role_{r.capitalize()}.png")))
    
    ranks = ["iron", "bronze", "silver", "gold", "platinum", "emerald", "diamond", "master", "grandmaster", "challenger"]
    rank_url = "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-{}.png"
    for r in ranks: tasks.append((rank_url.format(r), os.path.join(ui_dir, f"Rank_{r.capitalize()}.png")))

    return tasks

# ==========================================
# 3. CHƯƠNG TRÌNH CHÍNH (ĐA LUỒNG)
# ==========================================

def main():
    print("==================================================")
    print("🔥 KHỞI ĐỘNG HỆ THỐNG TẢI TÀI NGUYÊN BROADCAST 🔥")
    print("==================================================")
    version = get_latest_version()
    print(f"📌 Phiên bản dữ liệu: {version}\n")

    base_dir = "LOL_Broadcast_Assets_Final"
    os.makedirs(base_dir, exist_ok=True)

    print("⏳ Đang quét API và thiết lập danh sách tải...")
    all_tasks = []
    all_tasks.extend(gather_champion_tasks(version, base_dir))
    all_tasks.extend(gather_item_tasks(version, base_dir))
    all_tasks.extend(gather_augment_tasks(base_dir))
    all_tasks.extend(gather_misc_tasks(version, base_dir))

    total_files = len(all_tasks)
    print(f"🚀 TỔNG CỘNG: {total_files} file. Bắt đầu tải đa luồng...")

    downloaded_new = 0
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(download_file, task): task for task in all_tasks}
        
        completed = 0
        for future in as_completed(futures):
            result = future.result()
            completed += 1
            if result is True:
                downloaded_new += 1
            
            if completed % 100 == 0 or completed == total_files:
                percent = (completed / total_files) * 100
                print(f"🔄 Tiến độ: {completed}/{total_files} file ({percent:.1f}%)")

    print("\n==================================================")
    print(f"🏆 HOÀN TẤT TUYỆT ĐỐI! Đã tải/kiểm tra xong {total_files} file.")
    print(f"📁 Hãy mở thư mục: '{base_dir}' để kiểm tra thành quả.")
    print("==================================================")

if __name__ == "__main__":
    main()