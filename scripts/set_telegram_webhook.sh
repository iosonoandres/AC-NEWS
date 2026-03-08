#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  echo "Missing TELEGRAM_BOT_TOKEN"
  exit 1
fi

if [[ -z "${TELEGRAM_WEBHOOK_SECRET:-}" ]]; then
  echo "Missing TELEGRAM_WEBHOOK_SECRET"
  exit 1
fi

if [[ -z "${PUBLIC_BASE_URL:-}" ]]; then
  echo "Missing PUBLIC_BASE_URL (example: https://example.com)"
  exit 1
fi

WEBHOOK_URL="${PUBLIC_BASE_URL%/}/webhook/telegram/${TELEGRAM_WEBHOOK_SECRET}"

curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"${WEBHOOK_URL}\"}"

echo ""
echo "Webhook configured: ${WEBHOOK_URL}"
