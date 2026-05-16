import os
import tempfile
from flask import jsonify, request, current_app

from app import logic
import config

@current_app.route('/api/hud')
def get_arena_data():
    """Endpoint chính: Lấy dữ liệu game, xử lý và trả về định dạng cho HUD."""
    game_data = logic._fetch_live_game_data()
    if not game_data:
        return jsonify({"status": "waiting", "error": "Could not connect to game client. Is the game running?"}), 200

    try:
        all_players = game_data.get("allPlayers", [])
        all_players.sort(key=lambda p: p.get('participantID', 0))
        
        teams = {}
        for i in range(0, len(all_players), config.TEAM_SIZE):
            team_id = (i // config.TEAM_SIZE) + 1
            if team_id > config.MAX_TEAMS_IN_HUD:
                break
            
            player_group = all_players[i:i + config.TEAM_SIZE]
            team_key = f"team_{team_id}"
            teams[team_key] = [logic._transform_player_data(p) for p in player_group]
        
        game_time = game_data.get("gameData", {}).get("gameTime", 0)
        return jsonify({"status": "in_game", "time": game_time, "teams": teams})

    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred during data transformation: {e}", exc_info=True)
        return jsonify({"status": "error", "error": "An internal error occurred while processing game data."}), 500

@current_app.route('/api/sync_match', methods=['GET'])
def sync_match():
    """API để đồng bộ Lõi nâng cấp của trận đấu gần nhất qua tên người chơi."""
    game_name = request.args.get("gameName")
    tag_line = request.args.get("tagLine")
    
    # Kiểm tra và thông báo lỗi cụ thể hơn cho từng tham số bị thiếu
    missing_params = []
    if not game_name:
        missing_params.append("`gameName`")
    if not tag_line:
        missing_params.append("`tagLine`")

    if missing_params:
        error_message = f"Thiếu các tham số bắt buộc: {', '.join(missing_params)}."
        return jsonify({"status": "error", "message": error_message}), 400
        
    response_data, status_code = logic.sync_match_data(game_name, tag_line)
    return jsonify(response_data), status_code
