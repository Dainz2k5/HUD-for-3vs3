import requests
from flask import current_app
import config
from . import utils

# Bộ nhớ đệm lưu Lõi lấy từ trận đấu trực tuyến trên Server Riot
MATCH_AUGMENTS_CACHE = {}

def _fetch_live_game_data():
    """Hàm con: Chỉ thực hiện việc gọi API và trả về dữ liệu JSON."""
    try:
        response = requests.get(config.LIVE_API_URL, verify=False, timeout=1)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        current_app.logger.warning(f"Could not connect to Live API: {e}")
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
        "items": [
            {"id": it["id"], "slot": it["slot"], "icon": utils.resolve_item_icon(it["id"])}
            for it in items
        ],
        "augments_urls": assigned_augs, # Lấy từ cache đã đồng bộ
        "summoners": [
            utils.resolve_spell_icon(s1_name),
            utils.resolve_spell_icon(s2_name)
        ]
    }

def sync_match_data(game_name, tag_line):
    """Lấy dữ liệu Lõi từ trận Arena gần nhất của người chơi qua Riot API."""
    global MATCH_AUGMENTS_CACHE
    headers = {"X-Riot-Token": config.RIOT_API_KEY}

    try:
        # Bước 1: Lấy PUUID
        account_url = f"https://{config.RIOT_API_REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        acc_res = requests.get(account_url, headers=headers, timeout=10)
        if acc_res.status_code == 403:
            return {"status": "error", "message": f"Lỗi 403 Forbidden. Vui lòng kiểm tra lại RIOT_API_KEY trong file config.py. Key có thể đã hết hạn hoặc không hợp lệ."}, 403
        if acc_res.status_code != 200:
            return {"status": "error", "message": f"Không tìm thấy tài khoản: {game_name}#{tag_line} (Code: {acc_res.status_code})"}, acc_res.status_code
        puuid = acc_res.json().get("puuid")
        
        # Bước 2: Tìm ID trận Arena gần nhất (Queue ID 1700)
        # Tăng count lên 5 để tìm trong 5 trận gần nhất, tăng khả năng tìm thấy trận Arena.
        match_list_url = f"https://{config.RIOT_API_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue=1700&start=0&count=20"
        match_res = requests.get(match_list_url, headers=headers, timeout=10)
        match_res.raise_for_status()
        match_ids = match_res.json()
        if not match_ids:
            message = "Không tìm thấy lịch sử trận Arena nào cho người chơi này. Vui lòng thử với một người chơi khác hoặc đảm bảo họ đã chơi Arena gần đây."
            current_app.logger.info(f"Sync failed for {game_name}#{tag_line}: {message}")
            return {"status": "error", "message": message}, 404
        match_id = match_ids[0]
        
        # Bước 3: Lấy chi tiết trận đấu
        match_detail_url = f"https://{config.RIOT_API_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        detail_res = requests.get(match_detail_url, headers=headers, timeout=10)
        detail_res.raise_for_status()
        match_data = detail_res.json()
        
        participants = match_data.get("info", {}).get("participants", [])
        temp_cache = {}
        for p in participants:
            p_name = utils.normalize_key(p.get("riotIdGameName", p.get("summonerName", "")))
            augs_list = [utils.resolve_augment_icon_by_id(p.get(f"playerAugment{i}")) for i in range(1, 7) if p.get(f"playerAugment{i}", 0) > 0]
            temp_cache[p_name] = augs_list
            
        MATCH_AUGMENTS_CACHE = temp_cache
        return {"status": "ok", "message": f"Đồng bộ thành công trận {match_id}. Đã nạp Lõi cho {len(temp_cache)} người chơi!"}, 200
        
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Lỗi API Riot: {e}"}, 500
    except Exception as e:
        current_app.logger.error(f"Lỗi không xác định khi đồng bộ trận đấu: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}, 500
