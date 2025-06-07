# Tài liệu Game Battleship

Tài liệu này mô tả game Battleship, viết bằng Python, dùng Pygame, hỗ trợ chơi đơn và chơi mạng, với AI đa dạng và giao tiếp mạng mạnh mẽ.

---

## Nội dung

1. [Tổng quan](#tổng-quan)
2. [Tính năng](#tính-năng)
3. [Hệ thống AI](#hệ-thống-ai)
4. [Mạng](#mạng)
5. [Cách dùng](#cách-dùng)
6. [Cải tiến tương lai](#cải-tiến-tương-lai)

---

## Tổng quan

Battleship là game chiến thuật hải quân, hỗ trợ:
- **Chơi đơn**: Đấu với AI nhiều cấp độ.
- **Chơi mạng**: Kết nối server đấu với người khác.
- **AI nâng cao**: Từ ngẫu nhiên đến MCTS, mạng nơ-ron.
- **Mạng**: Giao tiếp client-server, xử lý bất đồng bộ.
- **Debug**: Bản đồ nhiệt, FPS, overlay.

---

## Tính năng

- Chế độ chơi đơn/nhiều người.
- Giao diện: Chuột đặt tàu, bắn; phím tắt (ESC, F1-F5).
- Mạng: Kết nối server.
- AI: Nhiều cấp độ, học hỏi.
- Cài đặt: Âm lượng, ngôn ngữ, lưu vào `preferences.json`.

---

## Hệ thống AI

- **Dễ**: Bắn ngẫu nhiên.
- **Trung bình**: Săn-đuổi, mẫu checkerboard.
- **Khó**: Thích nghi với cách đặt tàu.
- **Chuyên gia**: MCTS (200 mô phỏng).
- **Bậc thầy**: Mạng nơ-ron (chưa huấn luyện).
- **Ác mộng**: MCTS (500 mô phỏng, 5 giây).

---

## Mạng

- Kết nối server (mặc định: `127.0.0.1:8888`).
- Tin nhắn: `GAME_START`, `ATTACK`, `WIN`...
- Xử lý bất đồng bộ, heartbeat đo ping, chống lỗi.

---

## Cách dùng

1. **Yêu cầu**:
   - Python 3.x, Pygame (`pip install pygame`).
   - Server Battleship (cho chơi mạng).

2. **Chạy**:
   ```bash
   python main.py
   ```
   - Mở cửa sổ 1200x650, vào menu chọn mode.

3. **Điều khiển**:
   - Chuột: Đặt tàu, bắn.
   - R/Space: Xoay tàu.
   - ESC: Menu/thoát.
   - F1: Trợ giúp.
   - F3: Bật FPS.
   - F4: Debug.

4. **Cấu hình**:
   - Chỉnh `preferences.json` (âm lượng, tên...).
   - Tùy chỉnh AI trong `ai_config.json`.

5. **Log**:
   - Lưu trong `battleship.log`.

---

## Cải tiến tương lai

- **AI**: Huấn luyện nơ-ron, tối ưu MCTS.
- **Mạng**: Tái kết nối, xem trận đấu, danh sách server.
- **UI**: Menu cài đặt, hiệu ứng đẹp hơn.
- **Tính năng**: Tăng sức mạnh, tùy chỉnh bàn, xem lại trận.
- **Hiệu suất**: Biểu đồ thống kê, bảng xếp hạng.

--- 

