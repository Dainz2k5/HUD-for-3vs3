import os

# --- Cấu hình chung ---
APP_ROOT = os.path.dirname(__file__)
DEBUG_MODE = True
SERVER_PORT = 5000

# --- Cấu hình Game & API ---
TEAM_SIZE = 3
MAX_TEAMS_IN_HUD = 6
NORMAL_ITEM_SLOT_LIMIT = 6
LIVE_API_URL = "https://127.0.0.1:2999/liveclientdata/allgamedata"

# --- Cấu hình Riot API (lấy từ developer.riotgames.com) ---
# Ưu tiên lấy key từ biến môi trường, nếu không có thì dùng key được viết cứng bên dưới.
# Đảm bảo bạn đã thay thế "RGAPI-..." bằng key mới nhất của bạn.
RIOT_API_KEY = os.getenv("RIOT_API_KEY", "RGAPI-965204b7-00d3-46dd-918b-c0ff9d7d4adb")
RIOT_API_REGION = "asia" # americas, asia, europe, sea

# --- Cấu hình đường dẫn ---
ASSET_FOLDER_NAME = "static"
ASSET_ROOT = os.path.join(APP_ROOT, "app", ASSET_FOLDER_NAME)
CHAMPION_ICON_DIR = os.path.join(ASSET_ROOT, "Champion_Icons")
ITEM_ICON_DIR = os.path.join(ASSET_ROOT, "Items")
SPELL_ICON_DIR = os.path.join(ASSET_ROOT, "Spells")
AUGMENT_ICON_DIR = os.path.join(ASSET_ROOT, "Augments")
LOL_LOG_PATH = "C:\\Riot Games\\League of Legends\\Logs\\Game - R3d Logs"
LOL_CLIENT_PATH = "C:\\Riot Games\\League of Legends"
CD_ARENA_JSON_PATH = os.path.join(APP_ROOT, "arena_augments.json")
