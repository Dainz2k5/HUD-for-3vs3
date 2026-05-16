# LOL Broadcast Tool

Một công cụ hiển thị thông tin trận đấu Võ Đài (Arena) trong game Liên Minh Huyền Thoại cho mục đích broadcast, streaming, hỗ trợ cả game đang chơi và replay.

## Tính năng

- Hiển thị thông tin người chơi: Tên, tướng, trang bị, lõi nâng cấp, phép bổ trợ.
- Tự động cập nhật theo thời gian thực qua Live Client API.
- Giao diện HUD được thiết kế để chèn vào các phần mềm streaming như OBS.

## Cài đặt & Cấu hình

1.  Clone repository này về máy.
2.  **Cấu hình API Key**:
    - Vào file `config.py`.
    - Thay thế giá trị `RGAPI-YOUR-ACTUAL-KEY-HERE` của biến `RIOT_API_KEY` bằng API key của bạn lấy từ Riot Developer Portal.
3.  **Tải dữ liệu Lõi (Augments)**:
    - Chạy script sau để tự động tải file `arena_augments.json` (chứa định nghĩa các lõi) về thư mục gốc:
    ```bash
    python scripts/download_arena_json.py
    ```
4.  **Cài đặt thư viện**:
    ```bash
    pip install -r requirements.txt
    ```
5.  (Tùy chọn) Chạy script để tải về các ảnh lõi nâng cấp mới nhất về máy (giúp load ảnh nhanh hơn):
    ```bash
    python scripts/download_augments.py
    ```

## Sử dụng

1.  Chạy ứng dụng web:
    ```bash
    python run.py
    ```
2.  **Đồng bộ dữ liệu trận đấu (QUAN TRỌNG)**:
    - Trước khi hiển thị HUD, bạn cần phải đồng bộ dữ liệu lõi của trận đấu bạn muốn theo dõi.
    - Mở trình duyệt và truy cập URL sau, thay `TenNguoiChoi` và `VN2` bằng Riot ID của **bất kỳ người chơi nào** trong trận:
      `http://127.0.0.1:5000/api/sync_match?gameName=TenNguoiChoi&tagLine=VN2`
    - Bạn sẽ nhận được thông báo thành công. Hệ thống đã lưu lại lõi của tất cả người chơi trong trận đó.

3.  Mở trang HUD của bạn (ví dụ: `http://127.0.0.1:5000/hud.html`).
4.  Thêm nguồn trình duyệt (Browser Source) trong OBS với URL của trang HUD. HUD sẽ tự động lấy dữ liệu KDA/trang bị từ game client (nếu đang trong trận/replay) và kết hợp với dữ liệu lõi đã đồng bộ.
