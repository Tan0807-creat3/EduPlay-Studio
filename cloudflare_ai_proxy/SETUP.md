# Cloudflare AI Proxy - Hướng dẫn Setup

## Prerequisites
- Node.js và npm đã cài đặt
- Tài khoản Cloudflare (miễn phí)
- Groq API key (lấy tại https://console.groq.com - miễn phí)

## Bước 1: Cài đặt Wrangler CLI
```bash
npm install -g wrangler
```

## Bước 2: Login Cloudflare
```bash
wrangler login
```
Browser sẽ mở → Login vào Cloudflare

## Bước 3: Tạo Worker
```bash
cd cloudflare_ai_proxy
wrangler deploy
```

## Bước 4: Set Secrets (QUAN TRỌNG!)

### 4.1. Set TOKEN_SECRET
```bash
wrangler secret put TOKEN_SECRET
# Nhập một chuỗi ngẫu nhiên dài ít nhất 32 ký tự
# Ví dụ: my_super_secret_token_key_12345678901234567890
```

### 4.2. Set Groq API Keys
```bash
wrangler secret put GROQ_KEY_1
# Nhập Groq API key (bắt đầu với gsk_)

# Optional: Thêm keys để load balance
wrangler secret put GROQ_KEY_2
wrangler secret put GROQ_KEY_3
```

### 4.3. (Optional) Set Master Token
Nếu muốn có 1 token cố định bypass device_id check:
```bash
wrangler secret put PROXY_TOKEN
# Nhập token master bất kỳ
```

## Bước 5: Kiểm tra Deploy
```bash
curl https://YOUR_WORKER_NAME.YOUR_SUBDOMAIN.workers.dev/register \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"device_id":"test_device_123"}'
```

Response mong đợi:
```json
{"token":"base64_encoded_token_here"}
```

## Bước 6: Cập nhật EduPlay Studio

Mở `eduplay_studio/eduplay/core/ai_service.py`:

```python
DEFAULT_PROXY_BASE_URL = "https://YOUR_WORKER_NAME.YOUR_SUBDOMAIN.workers.dev/openai/v1"
```

Hoặc set biến môi trường:
```bash
set GROQ_BASE_URL=https://YOUR_WORKER_NAME.YOUR_SUBDOMAIN.workers.dev/openai/v1
```

## Cập nhật Secrets

### Xem secrets hiện tại
```bash
wrangler secret list
```

### Đổi secret
```bash
wrangler secret put TOKEN_SECRET
# Nhập giá trị mới
```

### Xóa secret
```bash
wrangler secret delete GROQ_KEY_2
```

## Reset toàn bộ tokens trên tất cả máy

**Chỉ cần đổi TOKEN_SECRET!**

```bash
wrangler secret put TOKEN_SECRET
# Nhập giá trị mới khác với giá trị cũ
```

Sau đó trên **MỌI MÁY CLIENT**, xóa file token cache:
```cmd
del "C:\Users\%USERNAME%\Documents\EduPlay\Settings\ai_proxy_token.txt"
```

Mở lại EduPlay Studio → App tự động register lại với TOKEN_SECRET mới.

## Monitoring

### Xem logs real-time
```bash
wrangler tail
```

### Xem metrics
Vào Cloudflare Dashboard → Workers & Pages → Metrics

## Troubleshooting

### Lỗi: "Error 1101: Worker threw exception"
- Kiểm tra code TypeScript có lỗi syntax không
- Chạy `wrangler deploy` lại

### Lỗi: "missing_token_secret"
```bash
wrangler secret put TOKEN_SECRET
```

### Lỗi: "missing_groq_key"
```bash
wrangler secret put GROQ_KEY_1
```

### Lỗi: "unauthorized" (401)
- Client gửi sai token hoặc device_id
- Xóa `ai_proxy_token.txt` trên client và mở lại app

### Lỗi rate limit (429)
- Thêm nhiều Groq API keys để load balance:
  ```bash
  wrangler secret put GROQ_KEY_2
  wrangler secret put GROQ_KEY_3
  ```

## Architecture

```
┌──────────────────┐
│  EduPlay Studio  │
│  (Client)        │
└────────┬─────────┘
         │
         │ POST /register {"device_id": "dev_xxx"}
         │ → Response: {"token": "xxx"}
         │
         │ POST /openai/v1/chat/completions
         │ Headers:
         │   Authorization: Bearer {token}
         │   X-Device-Id: dev_xxx
         │
         ▼
┌──────────────────────────┐
│  Cloudflare Worker       │
│  (Proxy + Auth)          │
│                          │
│  1. Verify token:        │
│     expected = HMAC(     │
│       TOKEN_SECRET,      │
│       X-Device-Id        │
│     )                    │
│     if token != expected │
│       return 401         │
│                          │
│  2. Forward to Groq API  │
│     with GROQ_KEY_1/2/3  │
│     (round-robin)        │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────┐
│  Groq API        │
│  api.groq.com    │
└──────────────────┘
```

## Security Notes

1. **TOKEN_SECRET** là yếu tố duy nhất xác thực → KHÔNG CHIA SẺ
2. Token được tạo động từ device_id → không cần database
3. Mỗi máy có device_id khác nhau → token khác nhau
4. Đổi TOKEN_SECRET → invalidate tất cả tokens cũ
5. DPAPI encryption trên Windows → token cache chỉ giải mã được trên máy đó

## Cost

Cloudflare Workers Free Tier:
- ✅ 100,000 requests/day
- ✅ 10ms CPU time/request
- ✅ Đủ cho ~1000 users/day

Groq API Free Tier:
- ✅ 30 requests/phút
- ✅ 14,400 tokens/phút
- ✅ Đủ cho development

Để scale lên production → cần thêm Groq API keys.
