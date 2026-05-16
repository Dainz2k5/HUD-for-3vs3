from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import os
import re
import requests
import urllib3
import unicodedata
import tempfile

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Cấu hình và Hằng số ---
# Gom tất cả các giá trị cấu hình và hằng số vào một chỗ để dễ quản lý
TEAM_SIZE = 3  # Chế độ Võ Đài mới có đội 3 người
MAX_TEAMS_IN_HUD = 6 # HUD hiện tại hỗ trợ tối đa 6 đội
NORMAL_ITEM_SLOT_LIMIT = 6 # Các slot trang bị thông thường (0-5)

# --- Khởi tạo ứng dụng Flask ---
app = Flask(__name__, static_folder="LOL_Broadcast_Assets_Final", static_url_path="/assets")
CORS(app)

LIVE_API_URL = "https://127.0.0.1:2999/liveclientdata/allgamedata"
ASSETS_BASE_URL = "http://127.0.0.1:5000/assets"
ASSET_ROOT = os.path.join(os.path.dirname(__file__), "LOL_Broadcast_Assets_Final")
CHAMPION_ICON_DIR = os.path.join(ASSET_ROOT, "Champion_Icons")
ITEM_ICON_DIR = os.path.join(ASSET_ROOT, "Items")
SPELL_ICON_DIR = os.path.join(ASSET_ROOT, "Spells")
AUGMENT_ICON_DIR = os.path.join(ASSET_ROOT, "Nang_Cap_Vo_Dai")
ITEM_JSON_URL = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/items.json"
ITEM_JSON_MAP = None

# Bảng tra cứu toàn diện để xử lý các tên tướng đặc biệt từ API
CHAMPION_NAME_MAP = {
    # Tên có nhiều chữ hoặc ký tự đặc biệt
    "aurelionsol": "AurelionSol",
    "belveth": "BelVeth",
    "drmundo": "DrMundo",
    "jarvaniv": "JarvanIV",
    "kaisa": "KaiSa",
    "kogmaw": "KogMaw",
    "masteryi": "MasterYi",
    "missfortune": "MissFortune",
    "tahmkench": "TahmKench",
    "twistedfate": "TwistedFate",
    "xinzhao": "XinZhao",
    "ksante": "KSante",
    # Tên có cách viết hoa đặc biệt
    "chogath": "ChoGath",
    "khazix": "KhaZix",
    "leblanc": "LeBlanc",
    "velkoz": "VelKoz",
    "reksai": "RekSai",
    "fiddlesticks": "FiddleSticks",
    # Tên API không khớp với tên file ảnh
    "wukong": "MonkeyKing",
    "renataglasc": "Renata",
    # Tên không phải tướng (phòng hờ)
    "ambessa": "Ambessa"
}

def clean_name_key(value):
    if not value:
        return ""
    normalized = re.sub(r"[\s'\.-]", "", value).lower()
    return normalized

def normalize_key(value):
    if not value:
        return ""
    return re.sub(r"[\s'’\.-_]+", "", value).lower()


def remove_html_and_parentheses(value: str) -> str:
    if not value:
        return ""
    # remove html tags
    v = re.sub(r"<[^>]+>", "", value)
    # remove parentheses and content inside
    v = re.sub(r"\(.*?\)", "", v)
    return v.strip()


def build_champion_icon_map():
    icons = {}
    if not os.path.isdir(CHAMPION_ICON_DIR):
        return icons
    for fn in os.listdir(CHAMPION_ICON_DIR):
        if not fn.lower().endswith(('.png', '.jpg', '.jpeg')):
            continue
        if '_Icon' in fn:
            key = fn.rsplit('_Icon', 1)[0]
        else:
            key = fn.rsplit('.', 1)[0]
        icons[normalize_key(key)] = fn
    return icons


def build_item_icon_map():
    icons = {}
    if not os.path.isdir(ITEM_ICON_DIR):
        return icons
    for fn in os.listdir(ITEM_ICON_DIR):
        m = re.search(r'_(\d+)\.(png|jpg|jpeg)$', fn)
        if m:
            icons[int(m.group(1))] = fn
    return icons


def build_spell_icon_map():
    icons = {}
    if not os.path.isdir(SPELL_ICON_DIR):
        return icons
    for fn in os.listdir(SPELL_ICON_DIR):
        if not fn.lower().startswith('spell_'):
            continue
        name = fn[len('spell_'):].rsplit('.', 1)[0]
        icons[normalize_key(name)] = fn
    return icons


def build_augment_icon_map():
    icons = {}
    if not os.path.isdir(AUGMENT_ICON_DIR):
        return icons
    for fn in os.listdir(AUGMENT_ICON_DIR):
        # map by numeric id if present anywhere in filename
        m = re.search(r'(?:augment)?(\d{2,6})', fn)
        if m:
            try:
                icons[int(m.group(1))] = fn
            except Exception:
                pass
        # also map by normalized base name (without _small/_large)
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
                item_id = item.get('id')
                icon_path = item.get('iconPath')
                if item_id and icon_path:
                    ITEM_JSON_MAP[item_id] = icon_path
    except Exception:
        pass
    return ITEM_JSON_MAP

CHAMPION_ICON_MAP = build_champion_icon_map()
ITEM_ICON_MAP = build_item_icon_map()
SPELL_ICON_MAP = build_spell_icon_map()
AUGMENT_ICON_MAP = build_augment_icon_map()


def resolve_champion_icon(champion_name):
    if not champion_name:
        return ""
    key = normalize_key(champion_name)
    filename = CHAMPION_ICON_MAP.get(key)
    if filename:
        return f"{ASSETS_BASE_URL}/Champion_Icons/{filename}"
    return f"https://ddragon.leagueoflegends.com/cdn/latest/img/champion/{champion_name}.png"


def resolve_item_icon(item_id):
    filename = ITEM_ICON_MAP.get(item_id)
    if filename:
        return f"{ASSETS_BASE_URL}/Items/{filename}"
    icon_map = load_remote_item_icon_map()
    icon_path = icon_map.get(item_id)
    if icon_path:
        return f"https://raw.communitydragon.org{icon_path}"
    return f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/item-icons/{item_id}.png"


def resolve_spell_icon(spell_name):
    if not spell_name:
        return ""
    # sanitize display name from API (remove HTML, parentheses)
    clean = remove_html_and_parentheses(spell_name)
    # remove any stray angle brackets or quotes
    clean = re.sub(r"[<>\"]+", "", clean).strip()

    # try direct filename match (preserves diacritics)
    key = normalize_key(clean)
    filename = SPELL_ICON_MAP.get(key)
    if filename:
        return f"{ASSETS_BASE_URL}/Spells/{filename}"

    # try ASCII fallback key (strip diacritics) to match mapped files
    try:
        ascii_name = unicodedata.normalize('NFKD', clean).encode('ascii', 'ignore').decode('ascii')
        ascii_key = normalize_key(ascii_name)
        filename = SPELL_ICON_MAP.get(ascii_key)
        if filename:
            return f"{ASSETS_BASE_URL}/Spells/{filename}"
    except Exception:
        pass

    # final fallback: build a safe, URL-encoded filename for DataDragon
    safe_name = re.sub(r"\s+", "", re.sub(r"[^\w\-\s]", "", clean))
    try:
        from urllib.parse import quote
        safe_name = quote(safe_name)
    except Exception:
        pass
    return f"https://ddragon.leagueoflegends.com/cdn/latest/img/spell/{safe_name}.png"


def resolve_augment_icon(item_id):
    # try numeric id
    filename = AUGMENT_ICON_MAP.get(item_id)
    if filename:
        return f"{ASSETS_BASE_URL}/Nang_Cap_Vo_Dai/{filename}"
    # try by normalized name key if item_id is actually a string name
    try:
        key = normalize_key(str(item_id))
        filename = AUGMENT_ICON_MAP.get(key)
        if filename:
            return f"{ASSETS_BASE_URL}/Nang_Cap_Vo_Dai/{filename}"
    except Exception:
        pass
    icon_map = load_remote_item_icon_map()
    icon_path = icon_map.get(item_id)
    if icon_path:
        return f"https://raw.communitydragon.org{icon_path}"
    return f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/item-icons/{item_id}.png"

def _fetch_live_game_data():
    """Hàm con: Chỉ thực hiện việc gọi API và trả về dữ liệu JSON."""
    try:
        response = requests.get(LIVE_API_URL, verify=False, timeout=1)
        response.raise_for_status()  # Tự động báo lỗi nếu status code không phải 200
        return response.json()
    except requests.exceptions.RequestException as e:
        app.logger.warning(f"Could not connect to Live API: {e}")
        return None

def _parse_player_items_and_augments(raw_items):
    """Hàm con: Tách trang bị và lõi nâng cấp từ danh sách thô."""
    items = []
    augments = []
    if not raw_items:
        return items, augments

    for it in sorted(raw_items, key=lambda item: item.get("slot", 99)):
        slot = it.get("slot", 99)
        item_id = it.get("itemID", 0)
        if item_id == 0:
            continue

        # Trang bị thông thường nằm ở 6 slot đầu
        if slot < NORMAL_ITEM_SLOT_LIMIT:
            items.append({"id": item_id, "slot": slot})
        # Các slot còn lại được coi là Lõi Nâng Cấp
        else:
            augments.append({"id": item_id, "name": it.get("displayName")})
    
    return items, augments

def _parse_player_summoner_spells(s_spells_data):
    """Hàm con: Trích xuất tên của các phép bổ trợ."""
    s1_name, s2_name = "", ""
    
    def parse_spell(spell_data):
        if not spell_data or not isinstance(spell_data, dict):
            return ""
        return spell_data.get("displayName") or spell_data.get("rawDisplayName") or ""

    if isinstance(s_spells_data, dict):
        s1_name = parse_spell(s_spells_data.get("summonerSpellOne"))
        s2_name = parse_spell(s_spells_data.get("summonerSpellTwo"))
    elif isinstance(s_spells_data, list):
        if len(s_spells_data) > 0:
            s1_name = parse_spell(s_spells_data[0])
        if len(s_spells_data) > 1:
            s2_name = parse_spell(s_spells_data[1])
            
    return s1_name, s2_name

def _transform_player_data(player_data):
    """Hàm con: Chuyển đổi dữ liệu thô của một người chơi thành định dạng cho HUD."""
    # 1. Tách trang bị và lõi
    raw_items = player_data.get("items", []) or []
    items, augments_from_items = _parse_player_items_and_augments(raw_items)

    # 2. Lấy Lõi từ trường "augments" nếu có (ưu tiên)
    augments = []
    raw_augments_field = player_data.get("augments", []) or []
    for raw_aug in raw_augments_field:
        aug_id = raw_aug.get("itemID") or raw_aug.get("id") or 0
        if aug_id > 0:
            augments.append({"id": aug_id, "name": raw_aug.get("displayName")})
    
    # Nếu không có, dùng danh sách lõi từ trang bị
    if not augments:
        augments = augments_from_items

    # 3. Lấy phép bổ trợ
    s_spells = player_data.get("summonerSpells", {}) or {}
    s1_name, s2_name = _parse_player_summoner_spells(s_spells)

    # 4. Lấy tên tướng chuẩn
    raw_champ_name = player_data.get("rawChampionName", "")
    # Tên chuẩn thường nằm sau "game_character_displayname_"
    champ_key = raw_champ_name.split('_')[-1] if raw_champ_name else player_data.get("championName", "")
    champ_display = player_data.get("championName", champ_key)

    # 5. Tạo đối tượng trả về
    return {
        "name": player_data.get("summonerName", ""),
        "champion": champ_display,
        "avatar": resolve_champion_icon(champ_key),
        "level": player_data.get("level", 1),
        "is_dead": player_data.get("isDead", False),
        "kills": player_data.get("scores", {}).get("kills", 0),
        "deaths": player_data.get("scores", {}).get("deaths", 0),
        "items": [
            {"id": it["id"], "slot": it["slot"], "icon": resolve_item_icon(it["id"])}
            for it in items
        ],
        "augments": [
            {"id": aug["id"], "name": aug.get("name", ""), "icon": resolve_augment_icon(aug["id"])}
            for aug in augments[:6] # Giới hạn 6 lõi để tránh tràn giao diện
        ],
        "summoners": [
            resolve_spell_icon(s1_name),
            resolve_spell_icon(s2_name)
        ]
    }

@app.route('/api/hud')
def get_arena_data():
    """Endpoint chính: Lấy dữ liệu game, xử lý và trả về định dạng cho HUD."""
    game_data = _fetch_live_game_data()
    if not game_data:
        return jsonify({"status": "waiting", "error": "Could not connect to game client. Is the game running?"}), 200

    try:
        all_players = game_data.get("allPlayers", [])
        # Sắp xếp người chơi theo ID để đảm bảo gom đội chính xác
        all_players.sort(key=lambda p: p.get('participantID', 0))
        
        teams = {}
        for i in range(0, len(all_players), TEAM_SIZE):
            team_id = (i // TEAM_SIZE) + 1
            if team_id > MAX_TEAMS_IN_HUD:
                break
            
            player_group = all_players[i:i + TEAM_SIZE]
            team_key = f"team_{team_id}"
            teams[team_key] = [_transform_player_data(p) for p in player_group]
        
        game_time = game_data.get("gameData", {}).get("gameTime", 0)
        return jsonify({"status": "in_game", "time": game_time, "teams": teams})

    except Exception as e:
        app.logger.error(f"An unexpected error occurred during data transformation: {e}", exc_info=True)
        return jsonify({"status": "error", "error": "An internal error occurred while processing game data."}), 500

if __name__ == '__main__':
    # Bật chế độ debug sẽ cho thông báo lỗi chi tiết hơn khi phát triển
    app.run(port=5000, debug=True)
