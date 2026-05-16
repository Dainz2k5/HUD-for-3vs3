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

# --- Các hàm Build Map (chạy một lần khi khởi động) ---

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
    """Tải và cache dữ liệu 'từ điển' Lõi từ file local hoặc CommunityDragon."""
    global CD_ARENA_DATA
    if CD_ARENA_DATA is not None:
        return CD_ARENA_DATA
    
    try:
        with open(config.CD_ARENA_JSON_PATH, "r", encoding="utf-8") as f:
            CD_ARENA_DATA = json.load(f)
            print(f"✅ Đã tải thành công file {os.path.basename(config.CD_ARENA_JSON_PATH)}")
    except Exception:
        print(f"⚠️ Không tìm thấy file {os.path.basename(config.CD_ARENA_JSON_PATH)}, đang tải online...")
        try:
            CD_ARENA_DATA = requests.get("https://raw.communitydragon.org/latest/cdragon/arena/en_us.json").json()
        except Exception as e:
            print(f"❌ Lỗi khi tải arena_augments.json online: {e}")
            CD_ARENA_DATA = {"data": {}} # Fallback to empty dict
    return CD_ARENA_DATA

# --- Các hàm Resolve Icon (dùng trong lúc xử lý request) ---

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
    
    # Fallback to Data Dragon
    ddragon_name = CHAMPION_NAME_MAP.get(key, champion_name.capitalize())
    return f"https://ddragon.leagueoflegends.com/cdn/latest/img/champion/{ddragon_name}.png"

def resolve_item_icon(item_id):
    filename = ITEM_ICON_MAP.get(item_id)
    if filename:
        return f"{ASSETS_BASE_URL}/Items/{filename}"
    
    # Fallback to Community Dragon
    icon_map = load_remote_item_icon_map()
    icon_path = icon_map.get(item_id)
    if icon_path:
        return f"https://raw.communitydragon.org{icon_path}"
    return f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/item-icons/{item_id}.png"

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
        ascii_key = normalize_key(ascii_name)
        filename = SPELL_ICON_MAP.get(ascii_key)
        if filename:
            return f"{ASSETS_BASE_URL}/Spells/{filename}"
    except Exception: pass

    safe_name = re.sub(r"\s+", "", re.sub(r"[^\w\-\s]", "", clean))
    return f"https://ddragon.leagueoflegends.com/cdn/latest/img/spell/{quote(safe_name)}.png"

def resolve_augment_icon_by_id(augment_id):
    """Dịch ID Lõi từ CommunityDragon thành Tên File ảnh local hoặc link ảnh online."""
    if not augment_id: return ""
    
    arena_data = load_cd_arena_data()
    aug_data = arena_data.get("data", {}).get(str(augment_id))
    if not aug_data:
        return ""
        
    icon_path = aug_data.get("iconSmall", "")
    if not icon_path: return ""

    filename = icon_path.split("/")[-1].lower()
    if os.path.isdir(config.AUGMENT_ICON_DIR):
        local_files = {fn.lower(): fn for fn in os.listdir(config.AUGMENT_ICON_DIR)}
        if filename in local_files:
            return f"{ASSETS_BASE_URL}/{os.path.basename(config.AUGMENT_ICON_DIR)}/{local_files[filename]}"
                
    clean_path = icon_path.replace("/lol-game-data/assets/", "").lower()
    return f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/{clean_path}"
