import requests
from flask import current_app
import config
from . import utils
import urllib3
import json

# Tắt cảnh báo khi gọi API của game client (Live Client API) vì nó dùng chứng chỉ tự ký (self-signed certificate).
# Đây là hành động an toàn vì kết nối này chỉ diễn ra bên trong máy tính của bạn.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Bộ nhớ đệm lưu Lõi lấy từ trận đấu trực tuyến trên Server Riot
MATCH_AUGMENTS_CACHE = {}
RINGS_CONFIG_CACHE = {}
PLAYER_ORDER_CACHE = {} # Lưu vị trí ghế ngồi chuẩn từ Riot API để chia team

# Nạp dữ liệu chi tiết Lõi Nâng Cấp từ file JSON khi ứng dụng khởi động
# Nạp dữ liệu chi tiết Lõi Nâng Cấp từ file JSON khi ứng dụng khởi động
# --- Cập nhật đoạn đọc file đầu trang của logic.py ---
AUGMENT_DATA = {}
AUGMENT_DATA_VI = {} # Bộ nhớ đệm lưu tên Tiếng Việt

# 1. Nạp dữ liệu Tiếng Anh (Gốc để đồng bộ ID nếu cần)
try:
    with open(config.CD_ARENA_JSON_PATH, 'r', encoding='utf-8') as f:
        raw_json = json.load(f)
        if isinstance(raw_json, dict) and "augments" in raw_json:
            for aug in raw_json["augments"]:
                if "id" in aug: AUGMENT_DATA[str(aug["id"])] = aug
        elif isinstance(raw_json, list):
            for aug in raw_json:
                if "id" in aug: AUGMENT_DATA[str(aug["id"])] = aug
        else:
            AUGMENT_DATA = raw_json
except Exception as e:
    print(f"[CẢNH BÁO] Không thể nạp file Tiếng Anh: {e}")

# 2. Nạp dữ liệu Tiếng Việt (🔥 THÊM PHẦN NÀY ĐỂ ĐỌC FILE TIẾNG VIỆT)
path_vi = getattr(config, "CD_ARENA_JSON_PATH_VI", "data/arena_augments_vi.json")
try:
    with open(path_vi, 'r', encoding='utf-8') as f:
        raw_json_vi = json.load(f)
        # Ép cấu trúc phẳng
        if isinstance(raw_json_vi, dict) and "augments" in raw_json_vi:
            for aug in raw_json_vi["augments"]:
                if "id" in aug: AUGMENT_DATA_VI[str(aug["id"])] = aug
        elif isinstance(raw_json_vi, list):
            for aug in raw_json_vi:
                if "id" in aug: AUGMENT_DATA_VI[str(aug["id"])] = aug
        else:
            AUGMENT_DATA_VI = raw_json_vi
    print(f"✅ [SYSTEM] Đã nạp thành công {len(AUGMENT_DATA_VI)} Lõi Nâng Cấp bằng Tiếng Việt.")
except Exception as e:
    print(f"[CẢNH BÁO] Chưa nạp được file Tiếng Việt tại {path_vi}. Vui lòng chạy script tải file trước!")


# --- Cập nhật hàm tra cứu chi tiết Lõi bên dưới của logic.py ---
def _get_augment_details(augment_id):
    """Tra cứu chi tiết của một Lõi Nâng Cấp bằng ID (Ưu tiên lấy ngôn ngữ Tiếng Việt và ảnh màu Local)."""
    aug_id_str = str(augment_id)
    
    # Ưu tiên lấy thông tin từ Từ điển Tiếng Việt
    details = AUGMENT_DATA_VI.get(aug_id_str) or AUGMENT_DATA.get(aug_id_str)
    
    # 🔥 FIX CHÍ MẠNG: Luôn gọi utils.py xử lý đường dẫn để kiểm tra file màu trong ổ D
    icon_path = utils.resolve_augment_icon_by_id(augment_id)
    
    if not details:
        return {
            "id": augment_id, 
            "name": "Lõi Không Xác Định", 
            "description": "Không tìm thấy dữ liệu.", 
            "icon": icon_path
        }
        
    return {
        "id": details.get("id"),
        "name": details.get("name"), # Tên Tiếng Việt chuẩn của game
        "description": details.get("description"),
        "icon": icon_path # Đường dẫn ảnh sạch có màu tuyệt đối từ ổ D hoặc Online đã xử lý
    }

def _fetch_live_game_data():
    """Hàm con: Chỉ thực hiện việc gọi API và trả về dữ liệu JSON."""
    try:
        # Cấu hình timeout=(connect, read). 
        # Đợi tối đa 0.5s để bắt tay kết nối, và 1.5s để đợi client trả dữ liệu về.
        response = requests.get(config.LIVE_API_URL, verify=False, timeout=(0.5, 1.5))
        response.raise_for_status()
        return response.json()
    except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
        # Đây là trạng thái bình thường khi game chưa bật hoặc chưa vào trận.
        # Thừa nhận âm thầm bằng cách trả về None, không in cảnh báo làm rác Terminal.
        return None
    except requests.exceptions.RequestException as e:
        # Chỉ ghi nhận các lỗi bất ngờ khác (ví dụ: lỗi HTTP từ phía client)
        current_app.logger.warning(f"Unexpected Live API error: {e}")
        return None

def _parse_player_items(raw_items):
    """Hàm con: Tách trang bị từ danh sách thô."""
    items = []
    if not raw_items:
        return items

    for it in sorted(raw_items, key=lambda item: item.get("slot", 99)):
        slot = it.get("slot", 99)
        item_id = it.get("itemID", 0)
        if item_id > 0 and slot < config.NORMAL_ITEM_SLOT_LIMIT:
            items.append({"id": item_id, "slot": slot})
    
    return items

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
    elif isinstance(s_spells_data, list) and len(s_spells_data) > 1:
        s1_name = parse_spell(s_spells_data[0])
        s2_name = parse_spell(s_spells_data[1])
            
    return s1_name, s2_name

def _transform_player_data(player_data):
    """Hàm con: Chuyển đổi dữ liệu thô của một người chơi thành định dạng cho HUD."""
    items = _parse_player_items(player_data.get("items", []))

    p_name_raw = player_data.get("riotIdGameName", player_data.get("summonerName", "")).split('#')[0]
    clean_name = utils.normalize_key(p_name_raw)
    assigned_augs = MATCH_AUGMENTS_CACHE.get(clean_name, [])

    s_spells = player_data.get("summonerSpells", {}) or {}
    s1_name, s2_name = _parse_player_summoner_spells(s_spells)

    raw_champ_name = player_data.get("rawChampionName", "")
    champ_key = raw_champ_name.split('_')[-1] if raw_champ_name else player_data.get("championName", "")
    champ_display = player_data.get("championName", champ_key)
    
    return {
        "name": p_name_raw,
        "champion": champ_display,
        "avatar": utils.resolve_champion_icon(champ_key),
        "level": player_data.get("level", 1),
        "is_dead": player_data.get("isDead", False),
        "kills": player_data.get("scores", {}).get("kills", 0),
        "deaths": player_data.get("scores", {}).get("deaths", 0),
        "assists": player_data.get("scores", {}).get("assists", 0), # 🔥 THÊM DÒNG NÀY ĐỂ BẮT DATA ASSISTS TỪ CLIENT RIOT
        "items": [
            {"id": it["id"], "slot": it["slot"], "icon": utils.resolve_item_icon(it["id"])}
            for it in items
        ],
        "augments": assigned_augs,
        "summoners": [
            utils.resolve_spell_icon(s1_name),
            utils.resolve_spell_icon(s2_name)
        ]
    }

def get_region_from_platform(platform_id):
    """
    Xác định khu vực API (routing value) từ Platform ID (server).
    Ví dụ: 'VN2' -> 'sea', 'KR' -> 'asia'.
    """
    # Ánh xạ từ Platform ID (viết thường) sang khu vực API của Riot.
    PLATFORM_TO_REGION_MAP = {
        # SEA
        'vn2': 'sea', 'sg2': 'sea', 'ph2': 'sea', 'th2': 'sea', 'tw2': 'sea',
        # ASIA
        'kr': 'asia', 'jp1': 'asia', 'oc1': 'asia',
        # AMERICAS
        'na1': 'americas', 'br1': 'americas', 'la1': 'americas', 'la2': 'americas', 'pbe': 'americas',
        # EUROPE
        'eun1': 'europe', 'euw1': 'europe', 'tr1': 'europe', 'ru': 'europe',
    }
    return PLATFORM_TO_REGION_MAP.get(platform_id.lower())

def sync_specific_match_data(match_id, api_region):
    """Lấy dữ liệu Lõi từ một ID trận đấu cụ thể qua Riot API."""
    global MATCH_AUGMENTS_CACHE, PLAYER_ORDER_CACHE
    headers = {"X-Riot-Token": config.RIOT_API_KEY}
    current_app.logger.info(f"Đang đồng bộ trận đấu cụ thể: {match_id} qua khu vực API: {api_region}")

    try:
        # Bước 1: Lấy chi tiết trận đấu trực tiếp từ ID
        match_detail_url = f"https://{api_region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        detail_res = requests.get(match_detail_url, headers=headers, timeout=10)
        
        if detail_res.status_code == 403:
             return {"status": "error", "message": f"Lỗi 403 Forbidden. Vui lòng kiểm tra lại RIOT_API_KEY trong file config.py. Key có thể đã hết hạn hoặc không hợp lệ."}, 403
        
        if detail_res.status_code == 404:
            return {"status": "error", "message": f"Không tìm thấy trận đấu với ID đầy đủ là '{match_id}' trên khu vực '{api_region}'. Vui lòng kiểm tra lại Platform ID."}, 404

        detail_res.raise_for_status() # Báo lỗi cho các status code 4xx, 5xx khác
        match_data = detail_res.json()

        # Kiểm tra xem có phải trận Arena không
        game_mode = match_data.get("info", {}).get("gameMode")
        if game_mode != "CHERRY":
             return {"status": "error", "message": f"Trận đấu {match_id} không phải là chế độ Arena (gameMode: {game_mode})."}, 400

        # Bước 2: Phân tách dữ liệu và nạp vào cache
        participants = match_data.get("info", {}).get("participants", [])
        temp_cache = {}
        temp_order = {}
        for idx, p in enumerate(participants):
            p_name_raw = p.get("riotIdGameName", p.get("summonerName", "")).split('#')[0]
            p_name = utils.normalize_key(p_name_raw)
            augs_list = []
            for i in range(1, 7):
                aug_id = p.get(f"playerAugment{i}")
                if aug_id and aug_id > 0:
                    augs_list.append(_get_augment_details(aug_id))
            temp_cache[p_name] = augs_list
            temp_order[p_name] = idx # Lưu số thứ tự của người chơi
            
        MATCH_AUGMENTS_CACHE = temp_cache
        PLAYER_ORDER_CACHE = temp_order
        return {"status": "ok", "message": f"Đồng bộ thành công trận {match_id}. Đã nạp Lõi cho {len(temp_cache)} người chơi!"}, 200
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Lỗi API Riot: {e}"}, 500
    except Exception as e:
        current_app.logger.error(f"Lỗi không xác định khi đồng bộ trận đấu: {e}", exc_info=True)
        return {"status": "error", "message": f"Lỗi hệ thống nội bộ: {str(e)}"}, 500

def sync_match_data(game_name, tag_line):
    """Lấy dữ liệu Đội hình và Lõi từ trận đấu LIVE đang diễn ra qua Riot API."""
    global MATCH_AUGMENTS_CACHE, PLAYER_ORDER_CACHE
    headers = {"X-Riot-Token": config.RIOT_API_KEY}
    current_app.logger.info(f"Đang đồng bộ Đội hình Live cho {game_name}#{tag_line} qua khu vực API: {config.RIOT_API_REGION}")

    try:
        # Bước 1: Lấy PUUID từ Riot Account API
        account_url = f"https://{config.RIOT_API_REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        acc_res = requests.get(account_url, headers=headers, timeout=10)

        if acc_res.status_code == 403:
            return {"status": "error", "message": "Lỗi 403 Forbidden. Vui lòng kiểm tra hoặc làm mới RIOT_API_KEY trong file config.py."}, 403
        if acc_res.status_code != 200:
            return {"status": "error", "message": f"Không tìm thấy tài khoản: {game_name}#{tag_line}"}, acc_res.status_code
        
        puuid = acc_res.json().get("puuid")
        
        # BƯỚC 2: KIỂM TRA TRẬN ĐẤU LIVE ĐANG DIỄN RA (Dùng Spectator-V5 API)
        spectator_url = f"https://{config.RIOT_API_REGION}.api.riotgames.com/lol/spectator/v5/active-games/by-puuid/{puuid}"
        spec_res = requests.get(spectator_url, headers=headers, timeout=10)
        
        if spec_res.status_code == 200:
            # NGƯỜI CHƠI ĐANG TRONG TRẬN ĐẤU LIVE THỰC TẾ!
            live_data = spec_res.json()
            participants = live_data.get("participants", [])
            
            temp_order = {}
            temp_cache = {}
            
            for p in participants:
                # Trích xuất tên người chơi chuẩn từ trường riotId hoặc summonerName công khai
                p_name_raw = p.get("riotId", "").split('#')[0] if p.get("riotId") else p.get("summonerName", "")
                if not p_name_raw:
                    continue
                    
                p_name = utils.normalize_key(p_name_raw)
                
                # SỬA LỖI CHÍ MẠNG: Lấy mã số Đội nhỏ trực tiếp của Riot làm trọng số sắp xếp (Ví dụ: 701, 702...)
                temp_order[p_name] = p.get("teamId", 999)
                temp_cache[p_name] = [] # Trận live chưa kết thúc nên danh sách Lõi tạm thời để trống
                
            PLAYER_ORDER_CACHE = temp_order
            MATCH_AUGMENTS_CACHE = temp_cache
            return {"status": "ok", "message": f"Đồng bộ thành công! Đã quét và sắp xếp cấu trúc 6 đội nhỏ cho 18 người chơi theo thời gian thực."}, 200

        # Bước 3: Dự phòng nếu người chơi không trong trận, lấy trận đấu Arena cũ đã hoàn thành gần nhất
        match_list_url = f"https://{config.RIOT_API_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue=1700&start=0&count=20"
        match_res = requests.get(match_list_url, headers=headers, timeout=10)
        match_res.raise_for_status()
        match_ids = match_res.json()
        
        if not match_ids:
            return {"status": "error", "message": "Không tìm thấy lịch sử trận Võ Đài nào của người chơi này."}, 404
            
        match_id = match_ids[0]
        return sync_specific_match_data(match_id, config.RIOT_API_REGION)
        
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Lỗi kết nối API Riot: {e}"}, 500
    except Exception as e:
        current_app.logger.error(f"Lỗi hệ thống đồng bộ: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}, 500