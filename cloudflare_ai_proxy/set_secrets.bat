@echo off
echo Set Cloudflare Secrets
echo.

echo Setting PROXY_TOKEN...
echo Edubot-1234513-eduplaystudio9832| npx wrangler secret put PROXY_TOKEN

echo.
echo Done! Now deploy:
echo npx wrangler deploy
pause
