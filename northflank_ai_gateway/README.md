# EduPlay Northflank AI Gateway

Gateway Node.js cho `EduPlay Studio` khi chạy AI qua Northflank.

## Mục tiêu

- Giữ Groq API key thật ở phía server.
- Mỗi máy có `device key` riêng, lưu ẩn trong client.
- Server bind `device_id + device_key + machine_fingerprint` để key đó chỉ dùng được cho đúng máy đã đăng ký.
- Khi Northflank cold-start, client có thể retry và hiện trạng thái "Đang gọi AI..." trong khung chat.
- Hỗ trợ nhiều Groq key và tự xoay vòng theo kiểu round-robin.
- Key nào bị `429` sẽ được cho nghỉ tạm trong một khoảng thời gian, request sau sẽ tự né key đó.
- `GET /health` trả về trạng thái từng key để dễ theo dõi trên server.

## Endpoints

- `GET /health`
- `POST /device/register`
- `POST /openai/v1/chat/completions`

## Environment Variables

- `APP_TOKEN_SECRET`: bắt buộc, secret ký access token và hash `device key`.
- `GROQ_API_KEYS`: danh sách Groq key phân tách bởi dấu phẩy, khoảng trắng hoặc `;`.
- `GROQ_API_KEY`: Groq key đơn lẻ.
- `GROQ_KEY_1`, `GROQ_KEY_2`, `GROQ_KEY_3`: lựa chọn tương thích với cấu hình cũ.
- `GROQ_API_BASE_URL`: mặc định `https://api.groq.com/openai/v1`.
- `GROQ_KEY_COOLDOWN_SEC`: số giây cho key nghỉ khi bị `429`, mặc định `900`.
- `GROQ_INVALID_KEY_COOLDOWN_SEC`: số giây cho key nghỉ khi bị `401/403`, mặc định `3600`.
- `GROQ_NETWORK_ERROR_COOLDOWN_SEC`: số giây cho key nghỉ khi lỗi mạng, mặc định `20`.
- `PORT`: cổng chạy server, mặc định `3000`.
- `DATA_DIR`: thư mục lưu file bind thiết bị, mặc định `./data`.
- `ACCESS_TOKEN_TTL_SEC`: thời gian sống của access token, mặc định `604800` giây.

## Chạy local

```bash
cd northflank_ai_gateway
set APP_TOKEN_SECRET=replace_me_with_long_random_secret
set GROQ_KEY_1=gsk_xxx_1
set GROQ_KEY_2=gsk_xxx_2
set GROQ_KEY_3=gsk_xxx_3
set GROQ_KEY_COOLDOWN_SEC=900
npm start
```

Health check:

```bash
curl http://localhost:3000/health
```

## Deploy Northflank

1. Tạo service mới từ thư mục `northflank_ai_gateway`.
2. Build command: để trống.
3. Start command: `npm start`
4. Runtime: Node.js 18+.
5. Mount volume bền vững vào `DATA_DIR` nếu muốn device binding không mất sau redeploy.
6. Set biến môi trường:

```text
APP_TOKEN_SECRET=...
GROQ_KEY_1=...
GROQ_KEY_2=...
GROQ_KEY_3=...
GROQ_KEY_COOLDOWN_SEC=900
GROQ_INVALID_KEY_COOLDOWN_SEC=3600
GROQ_NETWORK_ERROR_COOLDOWN_SEC=20
DATA_DIR=/data/eduplay-ai
```

## Health Check Thông Minh

- `GET /health` giờ trả thêm:
  - `groq_ready_keys`
  - `groq_cooling_keys`
  - `key_states`
- Mỗi phần tử trong `key_states` có:
  - `label`
  - `status`
  - `cooldown_remaining_sec`
  - `last_status_code`
  - `last_error`
  - `success_count`
  - `fail_count`

Ví dụ:

```json
{
  "ok": true,
  "groq_keys": 3,
  "groq_ready_keys": 2,
  "groq_cooling_keys": 1,
  "key_states": [
    {
      "index": 1,
      "label": "GROQ_KEY_1",
      "status": "cooling_down",
      "cooldown_remaining_sec": 742,
      "last_status_code": 429
    },
    {
      "index": 2,
      "label": "GROQ_KEY_2",
      "status": "ready",
      "cooldown_remaining_sec": 0,
      "last_status_code": 200
    }
  ]
}
```

## Cách Hoạt Động Của 3 Key

1. Request mới sẽ bắt đầu từ key kế tiếp theo vòng tròn.
2. Nếu key hiện tại bị `429`, server đánh dấu key đó là `cooling_down`.
3. Trong thời gian cooldown, request tiếp theo sẽ tự bỏ qua key đó.
4. Hết cooldown, key sẽ tự được dùng lại.
5. Nếu key bị `401/403`, server vẫn cho nghỉ tạm lâu hơn để tránh spam key hỏng.
6. Nếu tất cả key đều đang cooldown, server trả lỗi `all_groq_keys_cooling_down` kèm `retry_after_sec`.

## Quy trình client

1. Client sinh `device_id`, `device_key`, `machine_fingerprint`.
2. Client gọi `POST /device/register`.
3. Server tạo hoặc xác minh binding cho thiết bị.
4. Server trả `access_token`.
5. Các request chat tiếp theo gửi:
   - `Authorization: Bearer <access_token>`
   - `X-Device-Id`
   - `X-Device-Key`
   - `X-Machine-Fingerprint`
6. Server xác minh token lẫn binding trước khi forward sang Groq.

## Lưu ý bảo mật

- Không trả Groq API key thật về client.
- Nếu clone ổ cứng hoặc copy settings sang máy khác, binding sẽ lệch vì fingerprint và `device key` không khớp.
- Nếu muốn reset toàn bộ thiết bị đã bind, xóa file `device_bindings.json` trong `DATA_DIR`.
