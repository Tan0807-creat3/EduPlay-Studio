# EduPlay AI Proxy (Cloudflare Workers)

Proxy server cho EduPlay Studio - xác thực device-based token và forward requests tới Groq API.

## Quick Start

### 1) Cài đặt Wrangler CLI

```bash
npm install -g wrangler
wrangler login
```

### 2) Deploy worker

```bash
cd cloudflare_ai_proxy
wrangler deploy
```

### 3) Set secrets (QUAN TRỌNG!)

```bash
# Set TOKEN_SECRET để tạo/verify device tokens
wrangler secret put TOKEN_SECRET
# → Nhập chuỗi ngẫu nhiên ≥32 ký tự

# Set Groq API key (bắt buộc)
wrangler secret put GROQ_KEY_1
# → Nhập key từ https://console.groq.com

# Optional: Thêm keys để load balance
wrangler secret put GROQ_KEY_2
wrangler secret put GROQ_KEY_3

# Optional: Master token để bypass device check
wrangler secret put PROXY_TOKEN
```

### 4) Test

```bash
curl -X POST https://YOUR_WORKER.workers.dev/register \
  -H "Content-Type: application/json" \
  -d '{"device_id":"test_123"}'
```

Expected: `{"token":"..."}`

---

## Cơ chế Token

### Device Token (Mặc định - Khuyến nghị)
- Mỗi máy tự động tạo `device_id` từ machine info
- Client gọi `/register` với device_id → nhận token
- Token = HMAC_SHA256(TOKEN_SECRET, device_id)
- Mỗi máy có token riêng, tính động, không cần database
- Reset tất cả tokens: Đổi TOKEN_SECRET

### Master Token (Optional)
- Dùng `PROXY_TOKEN` cố định cho tất cả máy
- Bypass device_id check
- Dễ bị leak → không khuyến nghị cho production

---

## Environment Variables

### Bắt buộc
- `TOKEN_SECRET` - Secret để tạo device tokens (≥32 ký tự)
- `GROQ_KEY_1` - Groq API key chính

### Optional
- `GROQ_KEY_2` - Groq API key phụ (load balance)
- `GROQ_KEY_3` - Groq API key phụ (load balance)
- `PROXY_TOKEN` - Master token (bypass device check)

---

## API Endpoints

### POST /register
Tạo token cho device mới.

**Request:**
```json
{
  "device_id": "dev_abc123..."
}
```

**Response (200):**
```json
{
  "token": "base64_token_here"
}
```

**Errors:**
- `400` - bad_device_id
- `500` - missing_token_secret

### POST /openai/v1/chat/completions
Proxy Groq API chat completions.

**Headers:**
```
Authorization: Bearer {token}
X-Device-Id: {device_id}
Content-Type: application/json
```

**Body:** Theo Groq API spec

**Errors:**
- `401` - unauthorized (token sai hoặc missing device_id)
- `404` - not_found (endpoint sai)
- `500` - missing_groq_key (chưa set GROQ_KEY_1)

---

## Reset Token trên tất cả máy

**Chỉ cần đổi TOKEN_SECRET:**

```bash
wrangler secret put TOKEN_SECRET
# Nhập giá trị mới (khác cũ)
wrangler deploy
```

Sau đó trên **MỌI MÁY CLIENT**:
```cmd
del "%USERPROFILE%\Documents\EduPlay\Settings\ai_proxy_token.txt"
```

Mở lại EduPlay Studio → app tự động register lại.

---

## Monitoring

```bash
# Real-time logs
wrangler tail

# List secrets
wrangler secret list

# Deploy lại
wrangler deploy
```

---

## Troubleshooting

### Client: "Proxy token không hợp lệ hoặc không có quyền"
1. Xóa token cache: 
   ```cmd
   del "%USERPROFILE%\Documents\EduPlay\Settings\ai_proxy_token.txt"
   ```
2. Mở lại EduPlay Studio → app tự register lại

### Test /register: "missing_token_secret"
```bash
wrangler secret put TOKEN_SECRET
wrangler deploy
```

### Test chat: "missing_groq_key"
```bash
wrangler secret put GROQ_KEY_1
wrangler deploy
```

### Rate limit (429)
Thêm nhiều Groq API keys:
```bash
wrangler secret put GROQ_KEY_2
wrangler secret put GROQ_KEY_3
```

---

## Architecture

```
Client → [Device Token] → Cloudflare Worker → [GROQ_KEY] → Groq API
                ↑                  ↑
          HMAC verify         Load balance
        TOKEN_SECRET        GROQ_KEY_1/2/3
```

**Security:**
- ✅ Token được tạo động từ device_id
- ✅ Không cần database, không lưu tokens
- ✅ HMAC verification mỗi request
- ✅ Đổi TOKEN_SECRET → invalidate tất cả tokens
- ✅ DPAPI encryption trên client (Windows)

**Scalability:**
- ✅ Stateless worker
- ✅ Round-robin load balance nhiều Groq keys
- ✅ Auto-retry nếu 1 key bị rate limit
- ✅ Cloudflare free tier: 100k req/day

---

## Files

- `src/index.ts` - Worker source code
- `wrangler.toml` - Worker config
- `SETUP.md` - Hướng dẫn setup chi tiết
- `../FIX_PROXY_TOKEN_QUICK.md` - Troubleshooting cho end-users
- `../reset_token.bat` - Script reset token (Windows)
- `../test_proxy.bat` - Script test connection (Windows)
