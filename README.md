# AC-NEWS

Backend FastAPI per un bot news con focus Telegram, progettato per estendersi in futuro a WhatsApp.

## Stack
- Python 3.11+
- FastAPI
- Telegram Bot API (webhook)
- RSS aggregator con feed verticali per categoria (Gazzetta, Sky Sport, Vanity Fair, Il Sole 24 Ore, Wired, GialloZafferano, Cookist, Artribune, Exibart, Rolling Stone, altre fonti italiane)
- Persistenza JSON (account utenti, sessioni, commenti, valutazioni)

## Architettura

```
app/
  api/routes/               # Endpoint HTTP
  core/                     # Config e costanti
  domain/                   # Modelli dominio
  integrations/
    rss/                    # Client RSS e mapping fonti
    channels/
      telegram/             # Client Telegram + keyboards
      whatsapp/             # Stub integrazione futura
  services/                 # Business logic (auth, news, feedback, telegram flow)
  storage/                  # JSON store (users/sessions/comments/ratings)
  dependencies.py           # Wiring singleton servizi
  main.py                   # FastAPI app

scripts/set_telegram_webhook.sh

data/users.json

data/sessions.json

data/comments.json

data/ratings.json
```

## Flusso bot implementato
1. Utente apre il bot (`/start`)
2. Pulsante `📝 Registrati` -> inserimento username e password
3. Pulsante `🔐 Login` -> inserimento username e password
4. Solo dopo login: scelta categoria
5. Visualizzazione notizia con immagine (se presente nel feed)
6. Azioni per ogni notizia:
   - `➡️ Prossima notizia`
   - `💬 Commenta`
   - `🗂️ Vedi commenti`
   - valutazione `⭐️1` ... `⭐️5`
7. In messaggio notizia vengono mostrati:
   - media valutazione corrente
   - numero voti
   - numero commenti
8. Cleanup automatico: commenti/valutazioni di notizie più vecchie di 24h vengono rimossi
9. Filtro di rilevanza categoria lato codice (keyword scoring) per ridurre news off-topic
10. Alla notizia successiva viene rimosso il messaggio news precedente dalla chat (no coda infinita)
11. Cleanup automatico auth: sessioni vecchie >30 giorni rimosse; account rimossi solo se `last_login_at` >30 giorni

## Avvio locale

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Healthcheck:

```bash
curl http://127.0.0.1:8000/health
```

## Configurazione `.env`

```env
APP_NAME=AC-NEWS Bot Backend
APP_ENV=development
TELEGRAM_BOT_TOKEN=replace-with-botfather-token
TELEGRAM_WEBHOOK_SECRET=acnews-webhook-secret
PUBLIC_BASE_URL=https://your-ngrok-url.ngrok-free.app
REQUEST_TIMEOUT_SECONDS=10
NEWS_CACHE_TTL_SECONDS=300
FEEDBACK_TTL_HOURS=24
AUTH_RETENTION_DAYS=30
USERS_FILE=data/users.json
SESSIONS_FILE=data/sessions.json
COMMENTS_FILE=data/comments.json
RATINGS_FILE=data/ratings.json
```

## Webhook Telegram
Serve un URL pubblico HTTPS (es. ngrok).

```bash
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_WEBHOOK_SECRET="..."
export PUBLIC_BASE_URL="https://your-domain.com"
./scripts/set_telegram_webhook.sh
```

Webhook endpoint atteso:
`POST /webhook/telegram/{TELEGRAM_WEBHOOK_SECRET}`

## Test

```bash
pytest -q
```
