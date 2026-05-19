import os
import re
import requests
import json
import unicodedata
from urllib.parse import quote
import config

# --- Hằng số & Dữ liệu tra cứu ---

ITEM_JSON_URL = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/items.json"
ITEM_JSON_MAP = None
CD_ARENA_DATA = None

CHAMPION_NAME_MAP = {
    "aatrox": "Aatrox", "aurelionsol": "AurelionSol", "belveth": "BelVeth", 
    "drmundo": "DrMundo", "jarvaniv": "JarvanIV", "kaisa": "KaiSa", 
    "kogmaw": "KogMaw", "masteryi": "MasterYi", "missfortune": "MissFortune", 
    "tahmkench": "TahmKench", "twistedfate": "TwistedFate", "xinzhao": "XinZhao", 
    "ksante": "KSante", "chogath": "ChoGath", "khazix": "KhaZix", 
    "leblanc": "LeBlanc", "velkoz": "VelKoz", "reksai": "RekSai", 
    "fiddlesticks": "FiddleSticks", "wukong": "MonkeyKing", 
    "renataglasc": "Renata", "ambessa": "Ambessa"
}

# --- Hàm tiện ích ---

def normalize_key(value):
    if not value:
        return ""
    return re.sub(r"[\s'’\.-_]+", "", value).lower()

def remove_html_and_parentheses(value: str) -> str:
    if not value:
        return ""
    v = re.sub(r"<[^>]+>", "", value)
    v = re.sub(r"\(.*?\)", "", v)
    return v.strip()

# --- Các hàm Build Map ---

def build_icon_map(directory, pattern, key_transform=None):
    icons = {}
    if not os.path.isdir(directory):
        return icons
    for fn in os.listdir(directory):
        match = re.search(pattern, fn, re.IGNORECASE)
        if match:
            key = match.group(1)
            if key_transform:
                key = key_transform(key)
            icons[key] = fn
    return icons

def build_champion_icon_map():
    return build_icon_map(
        config.CHAMPION_ICON_DIR,
        r'^(.*?)(?:_Icon)?\.(png|jpg|jpeg)$',
        key_transform=normalize_key
    )

def build_item_icon_map():
    return build_icon_map(
        config.ITEM_ICON_DIR,
        r'_(\d+)\.(png|jpg|jpeg)$',
        key_transform=int
    )

def build_spell_icon_map():
    return build_icon_map(
        config.SPELL_ICON_DIR,
        r'^spell_(.*?)\.(png|jpg|jpeg)$',
        key_transform=normalize_key
    )

def build_augment_icon_map():
    icons = {}
    if not os.path.isdir(config.AUGMENT_ICON_DIR):
        return icons
    for fn in os.listdir(config.AUGMENT_ICON_DIR):
        m = re.search(r'(?:augment)?(\d{2,6})', fn)
        if m:
            icons[int(m.group(1))] = fn
        base = fn.rsplit('.', 1)[0]
        base = re.sub(r'_(small|large)$', '', base, flags=re.IGNORECASE)
        icons[normalize_key(base)] = fn
    return icons

def load_remote_item_icon_map():
    global ITEM_JSON_MAP
    if ITEM_JSON_MAP is not None:
        return ITEM_JSON_MAP
    ITEM_JSON_MAP = {}
    try:
        response = requests.get(ITEM_JSON_URL, verify=False, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for item in data:
                if item.get('id') and item.get('iconPath'):
                    ITEM_JSON_MAP[item['id']] = item['iconPath']
    except Exception:
        pass
    return ITEM_JSON_MAP

def load_cd_arena_data():
    global CD_ARENA_DATA
    if CD_ARENA_DATA is not None:
        return CD_ARENA_DATA
    
    # Ưu tiên đọc file Tiếng Việt của bạn trước để đồng bộ
    path_vi = getattr(config, "CD_ARENA_JSON_PATH_VI", "data/arena_augments_vi.json")
    target_path = path_vi if os.path.exists(path_vi) else config.CD_ARENA_JSON_PATH

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            CD_ARENA_DATA = {}
            if isinstance(raw_data, dict) and "augments" in raw_data:
                for aug in raw_data["augments"]:
                    CD_ARENA_DATA[str(aug["id"])] = aug
            elif isinstance(raw_data, dict) and "data" in raw_data:
                CD_ARENA_DATA = raw_data["data"]
            elif isinstance(raw_data, list):
                for aug in raw_data:
                    CD_ARENA_DATA[str(aug["id"])] = aug
            else:
                CD_ARENA_DATA = raw_data
    except Exception:
        CD_ARENA_DATA = {}
    return CD_ARENA_DATA

# --- Các hàm Resolve Icon ---

ASSETS_BASE_URL = f"http://127.0.0.1:{config.SERVER_PORT}/assets"
CHAMPION_ICON_MAP = build_champion_icon_map()
ITEM_ICON_MAP = build_item_icon_map()
SPELL_ICON_MAP = build_spell_icon_map()
AUGMENT_ICON_MAP = build_augment_icon_map()

def resolve_champion_icon(champion_name):
    if not champion_name: return ""
    key = normalize_key(champion_name)
    filename = CHAMPION_ICON_MAP.get(key)
    if filename:
        return f"{ASSETS_BASE_URL}/Champion_Icons/{filename}"
    ddragon_name = CHAMPION_NAME_MAP.get(key, champion_name.capitalize())
    return f"https://ddragon.leagueoflegends.com/cdn/latest/img/champion/{ddragon_name}.png"

def resolve_item_icon(item_id):
    if not item_id: return ""
    base_id = item_id if item_id <= 10000 else item_id % 10000
    filename = ITEM_ICON_MAP.get(base_id) or ITEM_ICON_MAP.get(item_id)
    if filename:
        return f"{ASSETS_BASE_URL}/Items/{filename}"
    icon_map = load_remote_item_icon_map()
    icon_path = icon_map.get(base_id) or icon_map.get(item_id)
    if icon_path:
        return f"https://raw.communitydragon.org{icon_path}"
    return f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/item-icons/{base_id}.png"

def resolve_spell_icon(spell_name):
    if not spell_name: return ""
    clean = remove_html_and_parentheses(spell_name)
    clean = re.sub(r"[<>\"]+", "", clean).strip()
    key = normalize_key(clean)
    filename = SPELL_ICON_MAP.get(key)
    if filename:
        return f"{ASSETS_BASE_URL}/Spells/{filename}"
    try:
        ascii_name = unicodedata.normalize('NFKD', clean).encode('ascii', 'ignore').decode('ascii')
        filename = SPELL_ICON_MAP.get(normalize_key(ascii_name))
        if filename: return f"{ASSETS_BASE_URL}/Spells/{filename}"
    except Exception: pass
    safe_name = re.sub(r"\s+", "", re.sub(r"[^\w\-\s]", "", clean))
    return f"https://ddragon.leagueoflegends.com/cdn/latest/img/spell/{quote(safe_name)}.png"


# ==================== SỬA ĐỔI HOÀN CHỈNH THUẬT TOÁN TÌM ẢNH CÓ MÀU Ở Ổ D ====================
def resolve_augment_icon_by_id(augment_id):
    """Ép buộc hệ thống load ảnh lớn có màu từ ổ D của bạn, chống dính file _small và sửa link online chuẩn _large."""
    if not augment_id: 
        return ""
    
    # Chuyển đổi sẵn các định dạng ID để tra cứu không bị sót
    id_str = str(augment_id)
    id_int = int(augment_id) if id_str.isdigit() else None
    
    # 🔥 SỬA LỖI CHÍ MẠNG: Import động để lấy dữ liệu từ RAM của logic.py
    # Tuyệt đối không gọi load_cd_arena_data() ở đây nữa để tránh vòng lặp nghẽn file JSON
    from app import logic
    arena_data_vi = getattr(logic, 'AUGMENT_DATA_VI', {})
    arena_data_en = getattr(logic, 'AUGMENT_DATA', {})
    
    # Tìm kiếm thông tin lõi từ bộ nhớ RAM đã nạp sẵn
    aug_data = arena_data_vi.get(id_str) or arena_data_vi.get(id_int) or arena_data_en.get(id_str) or arena_data_en.get(id_int)

    # 1. Tạo danh sách các tên file có màu (Large/Normal) để quét trong thư mục ổ D của bạn
    possible_filenames = []
    
    # Hướng 1: Quét file lưu theo ID số trực tiếp (Ví dụ: 1205.png, 1205_large.png)
    possible_filenames.append(f"{id_str}.png")
    possible_filenames.append(f"{id_str}_large.png")
    possible_filenames.append(f"{id_str}.jpg")
    
    # Hướng 2: Quét file lưu theo tên chữ bóc từ trường dữ liệu hệ thống
    filename_base = id_str # Mặc định nếu không bóc được chữ thì dùng ID số tạo tên file chữ
    
    if aug_data and isinstance(aug_data, dict):
        icon_path_field = aug_data.get("icon_path") or aug_data.get("iconSmall", "") or aug_data.get("icon_large", "")
        if icon_path_field:
            raw_filename = icon_path_field.split("/")[-1].lower() # Ví dụ: castle_small.png
            possible_filenames.append(raw_filename)
            
            # Trích xuất phần tên gốc loại bỏ đuôi mở rộng và hậu tố _small
            clean_name = raw_filename.rsplit('.', 1)[0]
            clean_name = clean_name.replace("_small", "").replace("_large", "")
            filename_base = clean_name
            
            # Đẩy các khả năng đặt tên màu vào danh sách check ổ D
            possible_filenames.append(f"{clean_name}.png")
            possible_filenames.append(f"{clean_name}_large.png")
            possible_filenames.append(f"{clean_name}.jpg")

    # 2. KIỂM TRA TRONG THƯ MỤC Ổ D CỦA BẠN (D:\CODE\app\static\Augments\icons\)
    if os.path.isdir(config.AUGMENT_ICON_DIR):
        local_files = {fn.lower(): fn for fn in os.listdir(config.AUGMENT_ICON_DIR)}
        
        for name in possible_filenames:
            if name.lower() in local_files:
                # 🔥 THÀNH CÔNG: Tìm thấy ảnh màu trong ổ D -> Trả về đường dẫn nội bộ ngay lập tức!
                return f"{ASSETS_BASE_URL}/Augments/icons/{local_files[name.lower()]}".replace("//", "/")

    # 3. FIX LINK ONLINE CHUẨN: Đồng bộ link CDN rực rỡ _large chuẩn 100% từ Riot nếu ổ D thiếu file
    # Ví dụ: Biến đổi thành https://raw.communitydragon.org/.../icons/castle_large.png
    return f"https://raw.communitydragon.org/latest/game/assets/ux/cherry/augments/icons/{filename_base}_large.png"