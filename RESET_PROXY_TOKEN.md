# Reset Proxy Token - Hướng dẫn

## Vấn đề
Token trong file `C:\Users\Admin\Documents\EduPlay\Settings\ai_proxy_token.txt` không còn hợp lệ.

## Giải pháp: Xóa token cũ để app tự register lại

### Bước 1: Xóa file token cũ
```cmd
del "C:\Users\Admin\Documents\EduPlay\Settings\ai_proxy_token.txt"
```

### Bước 2: Mở lại EduPlay Studio
App sẽ tự động:
1. Phát hiện không có token
2. Gọi `https://eduplay-ai-proxy.edubot-studio.workers.dev/register`
3. Gửi device_id của máy này
4. Nhận token mới và lưu vào file

### Bước 3: Kiểm tra
- Mở Edubot chat
- Gửi tin nhắn test
- Nếu vẫn lỗi → xem phần "Troubleshooting" bên dưới

---

## Cloudflare Workers: Cấu hình TOKEN_SECRET

### Yêu cầu
Cloudflare Workers cần biến môi trường `TOKEN_SECRET` để tạo token.

### Kiểm tra cấu hình
1. Vào Cloudflare Dashboard
2. Workers & Pages → `eduplay-ai-proxy`
3. Settings → Variables
4. Kiểm tra có biến `TOKEN_SECRET` không

### Nếu chưa có TOKEN_SECRET
```bash
cd cloudflare_ai_proxy
npx wrangler secret put TOKEN_SECRET
# Nhập secret bất kỳ (ít nhất 32 ký tự ngẫu nhiên)
```

### Deploy lại worker
```bash
cd cloudflare_ai_proxy
npx wrangler deploy
```

---

## Troubleshooting

### Lỗi: "Không lấy được proxy token"
**Nguyên nhân**: Không kết nối được `/register` endpoint

**Giải pháp**:
1. Kiểm tra internet
2. Test endpoint thủ công:
   ```cmd
   curl -X POST https://eduplay-ai-proxy.edubot-studio.workers.dev/register ^
     -H "Content-Type: application/json" ^
     -d "{\"device_id\":\"test_device_123\"}"
   ```
3. Nếu trả về `{"token":"..."}` → endpoint hoạt động
4. Nếu lỗi `missing_token_secret` → chưa set TOKEN_SECRET trên Cloudflare

### Lỗi: "Proxy token không hợp lệ hoặc không có quyền" (401/403)
**Nguyên nhân**: TOKEN_SECRET trên Cloudflare đã thay đổi

**Giải pháp**:
1. Xóa file token cũ (Bước 1 ở trên)
2. Mở lại app để register lại

### Lỗi: "missing_groq_key" (500)
**Nguyên nhân**: Cloudflare Workers chưa có Groq API keys

**Giải pháp**:
1. Vào Cloudflare Dashboard → Workers → Settings → Variables
2. Thêm biến:
   - `GROQ_KEY_1` = `gsk_...` (Groq API key)
   - `GROQ_KEY_2` = `gsk_...` (optional, để load balance)
   - `GROQ_KEY_3` = `gsk_...` (optional)
3. Deploy lại worker

---

## Alternative: Đổi sang Groq API trực tiếp

Nếu không muốn dùng proxy, bạn có thể:

1. Tạo Groq API key tại: https://console.groq.com
2. Mở Settings trong EduPlay Studio
3. Set:
   - `GROQ_BASE_URL` = `https://api.groq.com/openai/v1`
   - `GROQ_API_KEY` = `gsk_...` (key của bạn)
4. Khởi động lại app

---

## Cơ chế Token (Technical)

### Token Generation (Server)
```typescript
token = HMAC_SHA256(TOKEN_SECRET, device_id)
```

### Token Verification (Server)
```typescript
expected = HMAC_SHA256(TOKEN_SECRET, request.headers['x-device-id'])
if (request.headers['authorization'] !== `Bearer ${expected}`) {
  return 401
}
```

### Device ID Generation (Client)
```python
raw = f"{platform.node()}|{getpass.getuser()}|{uuid.getnode()}"
device_id = "dev_" + hashlib.sha256(raw.encode()).hexdigest()[:32]
```

Token **KHÔNG CẦN lưu trên server** - chỉ cần TOKEN_SECRET đúng là verify được!
