# Fix Proxy Token - Hướng dẫn nhanh

## Vấn đề
Edubot chat báo lỗi: **"Proxy token không hợp lệ hoặc không có quyền"**

## Nguyên nhân
Token trong file `ai_proxy_token.txt` không còn hợp lệ (có thể TOKEN_SECRET trên Cloudflare đã đổi).

---

## Giải pháp - CHỈ 2 BƯỚC! ⚡

### **Bước 1: Xóa token cũ**
Double-click: **`reset_token.bat`**

Hoặc chạy lệnh:
```cmd
del "%USERPROFILE%\Documents\EduPlay\Settings\ai_proxy_token.txt"
```

### **Bước 2: Mở lại EduPlay Studio**
App sẽ **TỰ ĐỘNG**:
1. Phát hiện không có token
2. Gọi `/register` lên Cloudflare
3. Nhận token mới
4. Lưu vào file

✅ **XONG!** Thử chat với Edubot lại.

---

## Nếu vẫn lỗi → Kiểm tra Cloudflare

### Test kết nối proxy
Double-click: **`test_proxy.bat`**

Hoặc:
```cmd
curl -X POST https://eduplay-ai-proxy.edubot-studio.workers.dev/register ^
  -H "Content-Type: application/json" ^
  -d "{\"device_id\":\"test_123\"}"
```

### Kết quả mong đợi
```json
{"token":"abc123xyz..."}
```

### Nếu lỗi "missing_token_secret"
Bạn cần **set TOKEN_SECRET trên Cloudflare**:

```bash
cd cloudflare_ai_proxy
wrangler secret put TOKEN_SECRET
# Nhập chuỗi ngẫu nhiên ít nhất 32 ký tự
# Ví dụ: my_secret_key_12345678901234567890abcdef

wrangler deploy
```

Sau đó quay lại **Bước 1** (reset token).

### Nếu lỗi "missing_groq_key"
Cloudflare chưa có Groq API key:

```bash
cd cloudflare_ai_proxy
wrangler secret put GROQ_KEY_1
# Nhập Groq API key (lấy tại https://console.groq.com)

wrangler deploy
```

---

## Reset token trên TẤT CẢ máy

**Chỉ cần đổi TOKEN_SECRET trên Cloudflare:**

```bash
cd cloudflare_ai_proxy
wrangler secret put TOKEN_SECRET
# Nhập giá trị mới (khác với cũ)
wrangler deploy
```

Sau đó trên **MỌI MÁY CLIENT**:
1. Chạy `reset_token.bat`
2. Mở lại EduPlay Studio

---

## Alternative: Dùng Groq API trực tiếp (không qua proxy)

Nếu không muốn dùng Cloudflare proxy:

1. Lấy Groq API key: https://console.groq.com
2. Mở EduPlay Studio Settings
3. Set:
   - Base URL: `https://api.groq.com/openai/v1`
   - API Key: `gsk_...` (key của bạn)

---

## Files tham khảo

- **`RESET_PROXY_TOKEN.md`** - Hướng dẫn chi tiết troubleshooting
- **`cloudflare_ai_proxy/SETUP.md`** - Hướng dẫn setup Cloudflare Workers từ đầu
- **`cloudflare_ai_proxy/README.md`** - Technical documentation
- **`reset_token.bat`** - Script xóa token cũ
- **`test_proxy.bat`** - Script test kết nối proxy

---

## TL;DR

```cmd
# Bước 1: Xóa token cũ
reset_token.bat

# Bước 2: Mở lại EduPlay Studio
# → App tự động lấy token mới

# Nếu vẫn lỗi → test proxy
test_proxy.bat

# Nếu proxy lỗi "missing_token_secret" → set trên Cloudflare
cd cloudflare_ai_proxy
wrangler secret put TOKEN_SECRET
wrangler deploy

# Quay lại Bước 1
```
