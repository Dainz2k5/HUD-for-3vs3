import os
import json
from flask import jsonify, request, current_app
from app import logic
import config
from flask import send_from_directory

@current_app.route('/hud_ring1')
def serve_ring1():
    return send_from_directory(os.path.join(current_app.root_path, 'static', 'hud_single'), 'hud_ring1.html')

@current_app.route('/hud_ring2')
def serve_ring2():
    return send_from_directory(os.path.join(current_app.root_path, 'static', 'hud_single'), 'hud_ring2.html')

@current_app.route('/hud_ring3')
def serve_ring3():
    return send_from_directory(os.path.join(current_app.root_path, 'static', 'hud_single'), 'hud_ring3.html')
@current_app.route('/api/hud')
def get_arena_data():
    """
    Endpoint chính: Lấy dữ liệu live client (bao gồm Trang bị, KDA, Tướng),
    sau đó ép phân đội nghiêm ngặt theo file nhập tay manual_teams.json.
    Đồng thời bảo lưu các Lõi nâng cấp do Admin chọn, chống bị ghi đè xóa sạch.
    """
    # ĐỒNG BỘ LIVE: Gọi trực tiếp API game đang chạy thay vì đọc file dump offline
    game_data = logic._fetch_live_game_data()
    
    if not game_data:
        return jsonify({"status": "waiting", "error": "Could not connect to game client. Is the game running?"}), 200

    try:
        all_players = game_data.get("allPlayers", [])
        
        # 1. ĐỌC FILE CẤU HÌNH NHẬP TAY THEO TÊN NGƯỜI CHƠI (Cơ chế Hot-reload mỗi giây)
        manual_mapping = {}
        mapping_path = os.path.join(config.APP_ROOT, "manual_teams.json")
        
        if os.path.exists(mapping_path):
            try:
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    raw_json = json.load(f)
                    # Chuẩn hóa toàn bộ tên người chơi trong file JSON để đối chiếu chính xác
                    manual_mapping = {logic.utils.normalize_key(str(k)): v for k, v in raw_json.items()}
            except Exception as e:
                current_app.logger.error(f"Lỗi định dạng hoặc đọc file manual_teams.json: {e}")

        # 2. KHỞI TẠO 6 HỘP ĐỘI NGHIÊM NGẶT (@uy tắc chế độ Võ Đài 3v3v3v3v3v3)
        teams = {f"team_{i}": [] for i in range(1, config.MAX_TEAMS_IN_HUD + 1)}
        fallback_counter = 1

        # 3. PHÂN LOẠI NGƯỜI CHƠI VÀO ĐỘI NHƯNG GIỮ NGUYÊN LUỒNG API VẬT PHẨM TRỰC TIẾP
        for p in all_players:
            # Chuyển đổi dữ liệu thô thành định dạng HUD chuẩn hóa (Bao gồm làm sạch tên)
            transformed_player = logic._transform_player_data(p)
            
            # Lấy tên sạch trực tiếp từ transformed_player để làm khóa tra cứu (Tuyệt đối không lấy từ p thô)
            clean_name = logic.utils.normalize_key(transformed_player["name"])
            
            # Kiểm tra xem người chơi mang định danh này được bạn gán cho Đội mấy
            team_num = manual_mapping.get(clean_name)
            
            if team_num and 1 <= int(team_num) <= config.MAX_TEAMS_IN_HUD:
                team_key = f"team_{team_num}"
            else:
                # Phương án dự phòng xếp tự động nếu bạn gõ thiếu tên người chơi trong file JSON
                team_key = f"team_{fallback_counter}"
                fallback_counter = (fallback_counter % config.MAX_TEAMS_IN_HUD) + 1
            
            # 🛠️ KIỂM TRA VÀ BẢO LƯU LÕI TỪ TRANG ADMIN (Đồng bộ chuẩn theo clean_name)
            existing_augs = logic.MATCH_AUGMENTS_CACHE.get(clean_name, [])
            if existing_augs:
                transformed_player["augments"] = existing_augs
            
            # Nạp dữ liệu người chơi kèm trọn bộ API vật phẩm live của họ vào hộp Đội
            teams[team_key].append(transformed_player)

        game_time = game_data.get("gameData", {}).get("gameTime", 0)
        return jsonify({"status": "in_game", "time": game_time, "teams": teams})

    except Exception as e:
        current_app.logger.error(f"Lỗi hệ thống khi xử lý ánh xạ dữ liệu HUD và vật phẩm: {e}", exc_info=True)
        return jsonify({"status": "error", "error": "Internal server error during data transformation."}), 500

@current_app.route('/api/sync_match', methods=['GET'])
def sync_match():
    """API để đồng bộ Lõi nâng cấp của trận đấu gần nhất qua tên người chơi."""
    game_name = request.args.get("gameName")
    tag_line = request.args.get("tagLine")
    
    missing_params = []
    if not game_name: missing_params.append("`gameName`")
    if not tag_line: missing_params.append("`tagLine`")

    if missing_params:
        return jsonify({"status": "error", "message": f"Thiếu các tham số bắt buộc: {', '.join(missing_params)}."}), 400
        
    response_data, status_code = logic.sync_match_data(game_name, tag_line)
    return jsonify(response_data), status_code

@current_app.route('/api/sync_match_by_id', methods=['GET'])
def sync_match_by_id():
    """API để đồng bộ Lõi nâng cấp của một trận đấu cụ thể qua ID."""
    match_id_number = request.args.get("matchId")
    platform_id = request.args.get("platformId")
    
    if not match_id_number or not platform_id:
        return jsonify({"status": "error", "message": "Thiếu tham số `matchId` hoặc `platformId`."}), 400
        
    full_match_id = f"{platform_id.upper()}_{match_id_number}"
    api_region = logic.get_region_from_platform(platform_id)
    
    if not api_region:
        return jsonify({"status": "error", "message": f"Không nhận dạng được Platform ID '{platform_id}'."}), 400
        
    response_data, status_code = logic.sync_specific_match_data(full_match_id, api_region)
    return jsonify(response_data), status_code

@current_app.route('/hud.html')
def serve_hud():
    return current_app.send_static_file('hud.html')

@current_app.route('/sync.html')
def serve_sync():
    return current_app.send_static_file('sync.html')

@current_app.route('/api/update_augment', methods=['POST'])
def update_player_augment():
    """API nhận dữ liệu Lõi nhập tay từ trang Admin và ghi đè vào Cache hệ thống."""
    try:
        data = request.get_json() or {}
        player_name = data.get("playerName")
        augment_ids = data.get("augmentIds", [])

        if not player_name:
            return jsonify({"status": "error", "message": "Thiếu tham số `playerName`."}), 400

        clean_name = logic.utils.normalize_key(player_name)

        detailed_augs = []
        for aug_id in augment_ids:
            if aug_id:
                detailed_augs.append(logic._get_augment_details(str(aug_id)))

        # Lưu cứng dữ liệu vào RAM
        logic.MATCH_AUGMENTS_CACHE[clean_name] = detailed_augs

        return jsonify({
            "status": "ok", 
            "message": f"Đã cập nhật thành công {len(detailed_augs)} lõi cho {player_name}!"
        }), 200

    except Exception as e:
        current_app.logger.error(f"Lỗi khi cập nhật lõi thủ công: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@current_app.route('/api/update_rings', methods=['POST'])
def update_rings():
    """API nhận cấu hình xếp cặp võ đài từ Admin và lưu vào bộ nhớ."""
    try:
        data = request.get_json()
        if data is None:
            data = {}
        logic.RINGS_CONFIG_CACHE = data
        return jsonify({"status": "ok", "message": "Cập nhật cấu hình cặp đấu thành công!"}), 200
    except Exception as e:
        current_app.logger.error(f"Lỗi khi cập nhật cấu hình vòng đấu: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@current_app.route('/api/get_rings', methods=['GET', 'POST'])
def get_rings():
    """API trả về hoặc cập nhật cấu hình cặp đấu hiện tại."""
    # Nếu Admin gửi cấu hình lên bằng phương thức POST
    if request.method == 'POST':
        try:
            data = request.get_json() or {}
            logic.RINGS_CONFIG_CACHE = {
                "ring1": data.get("ring1", [0, 0]),
                "ring2": data.get("ring2", [0, 0]),
                "ring3": data.get("ring3", [0, 0])
            }
            return jsonify({"status": "ok", "message": "Cập nhật thành công!"}), 200
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
            
    # Nếu gọi GET (Trình duyệt hoặc HUD lấy dữ liệu)
    # Cơ chế tự động sửa lỗi: Nếu RAM trống, thiết lập giá trị mặc định tránh làm sập HUD
    if not logic.RINGS_CONFIG_CACHE:
        logic.RINGS_CONFIG_CACHE = {
            "ring1": [0, 0],
            "ring2": [0, 0],
            "ring3": [0, 0]
        }
        
    return jsonify(logic.RINGS_CONFIG_CACHE), 200

@current_app.route('/api/augments_list')
def get_augments_list():
    """API đồng bộ thông minh danh sách Lõi phiên bản Tiếng Việt cho ô search admin.html."""
    processed_augments = {}
    base_data = logic.AUGMENT_DATA
    vi_data = getattr(logic, 'AUGMENT_DATA_VI', {})
    
    for aug_id, aug_info in base_data.items():
        if not aug_info or not isinstance(aug_info, dict):
            continue
            
        display_name = aug_info.get("name", "Unknown")
        
        vi_info = vi_data.get(str(aug_id))
        if vi_info and isinstance(vi_info, dict) and vi_info.get("name"):
            display_name = vi_info.get("name")
        elif str(aug_id) in vi_data and isinstance(vi_data[str(aug_id)], str):
            display_name = vi_data[str(aug_id)]
            
        processed_augments[str(aug_id)] = {
            "id": aug_id,
            "name": display_name.strip()
        }
        
    return jsonify(processed_augments), 200

@current_app.route('/admin.html')
def serve_admin():
    return current_app.send_static_file('admin.html')