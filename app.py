from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import re
import requests
import urllib3
import unicodedata
import tempfile
from werkzeug.utils import secure_filename
import ocr_augments

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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


def get_avatar_name(champion_name):
    """
    Chuyển đổi tên tướng từ API thành tên file ảnh chuẩn của Data Dragon.
    Nếu không nằm trong map thì loại bỏ khoảng trắng/kiểu viết khác.
    """
    if not champion_name:
        return "Unknown"

    lookup_key = clean_name_key(champion_name)
    if lookup_key in CHAMPION_NAME_MAP:
        return CHAMPION_NAME_MAP[lookup_key]

    return re.sub(r"[\s'\.-]", "", champion_name)


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


@app.route('/api/ocr', methods=['POST'])
def ocr_upload():
    # Accept multipart form upload with field 'image'
    if 'image' not in request.files:
        return jsonify({'error': 'no image file provided'}), 400
    f = request.files['image']
    if f.filename == '':
        return jsonify({'error': 'empty filename'}), 400
    filename = secure_filename(f.filename)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='_'+filename)
    f.save(tmp.name)
    try:
        result = ocr_augments.ocr_image_path(tmp.name)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return jsonify({'status': 'ok', 'ocr': result})


@app.route('/api/scan_augments', methods=['GET'])
def scan_augments():
    # scans c:/CODE/screenshot_data for images and returns detected augment cell texts
    folder = os.path.join(os.path.dirname(__file__), 'screenshot_data')
    res = ocr_augments.process_folder_for_augments(folder)
    return jsonify({'status': 'ok', 'results': res})

@app.route('/api/hud')
def get_arena_data():
    try:
        response = requests.get(LIVE_API_URL, verify=False, timeout=1)
        if response.status_code == 200:
            data = response.json()
            all_players = data.get("allPlayers", [])
            
            # Sắp xếp người chơi theo ID để đảm bảo gom đội chính xác trong Võ Đài
            all_players.sort(key=lambda p: p.get('participantID', 0))
            
            perfect_teams = {}
            team_counter = 1
            
            # Chế độ Võ Đài mới có các đội 3 người
            for i in range(0, len(all_players), 3):
                # HUD được thiết kế cho 6 đội, bỏ qua các đội thừa
                if team_counter > 6:
                    break
                
                player_trio = all_players[i:i+3]
                t_key = f"team_{team_counter}"
                perfect_teams[t_key] = []

                for p in player_trio:
                    # DEBUG: In tất cả keys của player object
                    print(f"\n=== Player: {p.get('summonerName')} ===")
                    print(f"All keys: {list(p.keys())}")
                    
                    # Kiểm tra xem có trường nào chứa augment không
                    for key in p.keys():
                        if 'augment' in key.lower():
                            print(f"Found augment-related key: {key} = {p[key]}")
                    
                    # Tách Lõi Nâng Cấp và trang bị / item chính
                    items = []
                    augments = []
                    raw_items = p.get("items", []) or []
                    
                    for it in sorted(raw_items, key=lambda item: item.get("slot", 0)):
                        slot = it.get("slot", 0)
                        item_id = it.get("itemID", 0)
                        if slot < 6:
                            items.append({"id": item_id, "slot": slot})
                        elif item_id > 0:
                            augments.append({"id": item_id, "name": it.get("displayName")})

                    # Nếu API có trường augments riêng, ưu tiên dùng trường này
                    for raw_aug in p.get("augments", []) or []:
                        aug_id = raw_aug.get("itemID") or raw_aug.get("id") or 0
                        if aug_id > 0:
                            augments.append({"id": aug_id, "name": raw_aug.get("displayName")})

                    def parse_spell(spell_data):
                        if not spell_data:
                            return ""
                        if isinstance(spell_data, dict):
                            display_name = spell_data.get("displayName") or spell_data.get("rawDisplayName")
                            return display_name or ""
                        return str(spell_data)

                    s_spells = p.get("summonerSpells", {}) or {}
                    if isinstance(s_spells, dict):
                        s1_raw = s_spells.get("summonerSpellOne") if isinstance(s_spells.get("summonerSpellOne"), dict) else {}
                        s2_raw = s_spells.get("summonerSpellTwo") if isinstance(s_spells.get("summonerSpellTwo"), dict) else {}
                    elif isinstance(s_spells, list):
                        s1_raw = s_spells[0].get("rawDisplayName", "") if len(s_spells) > 0 and isinstance(s_spells[0], dict) else ""
                        s2_raw = s_spells[1].get("rawDisplayName", "") if len(s_spells) > 1 and isinstance(s_spells[1], dict) else ""
                    else:
                        s1_raw = ""
                        s2_raw = ""

                    s1_id = parse_spell(s1_raw)
                    s2_id = parse_spell(s2_raw)

                    # Lấy tên tướng chuẩn nhất từ 'rawChampionName' hoặc championName
                    raw_champ_name = p.get("rawChampionName", "")
                    champ_key = raw_champ_name.split('_')[-1] if raw_champ_name else p.get("championName", "")
                    if normalize_key(champ_key) in ("name", "champion", "championname", "displayname"):
                        champ_key = p.get("championName", "")
                    champ_display = p.get("championName", champ_key)

                    perfect_teams[t_key].append({
                        "name": p.get("summonerName", ""),
                        "champion": champ_display,
                        "avatar": resolve_champion_icon(champ_key),
                        "level": p.get("level", 1),
                        "is_dead": p.get("isDead", False),
                        "kills": p.get("scores", {}).get("kills", 0),
                        "deaths": p.get("scores", {}).get("deaths", 0),
                        "items": [
                            {
                                "id": it["id"],
                                "slot": it["slot"],
                                "icon": resolve_item_icon(it["id"])
                            }
                            for it in items
                        ],
                        "augments": [
                            {
                                "id": aug["id"],
                                "name": aug.get("name", ""),
                                "icon": resolve_augment_icon(aug["id"])
                            }
                            for aug in augments[:6]
                        ],
                        "summoners": [
                            resolve_spell_icon(s1_id),
                            resolve_spell_icon(s2_id)
                        ]
                    })
                team_counter += 1
            
            return jsonify({"status": "in_game", "time": data.get("gameData", {}).get("gameTime", 0), "teams": perfect_teams})
    except Exception as e:
        return jsonify({"status": "waiting", "error": str(e)}), 200

if __name__ == '__main__':
    app.run(port=5000)
