# திருக்குறள் — Thirukkural

A Flask web app for reading all 1330 couplets (Kurals) of the Thirukkural, with
Tamil commentary from classical scholars, text-to-speech narration with live
word highlighting, and optional user accounts.

Built by the School of Computing, CINTEL Department, SRM Institute of Science
and Technology.

**Live:** https://thirukkural-evaz.onrender.com
(free-tier hosting — the first request after inactivity can take ~50s to wake up)

## Features

- **All 1330 kurals** across the three traditional sections (paals):
  அறத்துப்பால், பொருட்பால், காமத்துப்பால் — organized by iyal and chapter
  (அதிகாரம்), with global page numbers spanning the whole book.
- **Tamil commentary** for each kural, pulled from five classical
  commentators (சாலமன் பாப்பையா, மு. வரதராசனார், மு. கருணாநிதி, மணக்குடவர்,
  பரிமேலழகர்), plus the original English (V. V. S. Aiyar) translation and
  explanation as a fallback.
- **Text-to-speech playback** (Tamil, via gTTS) per kural or for a whole page
  at once, with a speaker panel that highlights the word currently being
  read.
- **Jump-to-kural search** — enter a kural number (1–1330) and it opens the
  right page, even if that kural lives in a different paal.
- **Accounts** — email/password signup and login, phone number + OTP login
  (logs the code to the console unless Twilio is configured), and Google
  OAuth login.
- **Audio caching** — generated speech is cached to disk by a hash of its
  text, so the same kural or page is never re-synthesized twice.

## Tech stack

| Layer     | Tech                                                          |
|-----------|----------------------------------------------------------------|
| Backend   | Flask 3, Flask-SQLAlchemy, Flask-Login, Flask-Migrate, Authlib |
| Database  | SQLite (local dev) / PostgreSQL (production)                  |
| Text-to-speech | gTTS (Google Translate TTS)                              |
| Frontend  | Server-rendered Jinja templates, Tailwind CSS (via CDN), vanilla JS |
| Production server | Gunicorn                                             |

## Project structure

```
tir/
├── app.py                        # Flask app: routes, auth, TTS, pagination
├── requirements.txt
├── Procfile                      # process command for deployment
├── start.sh                      # runs DB init, then Gunicorn
├── data/
│   ├── thirukkural.json          # all 1330 kurals (Tamil lines + English)
│   ├── thirukkural_meanings.json # Tamil commentary, keyed by kural number
│   └── detail.json               # paal → iyal → chapter structure
├── templates/                    # Jinja templates (base, landing, part, auth pages)
└── static/
    ├── app.js / part.js / landing.js
    ├── style.css / landing.css / animations.css
    └── audio/                    # generated TTS cache (git-ignored)
```

## Getting started

**Requirements:** Python 3.11+

```bash
git clone https://github.com/S-Harshni/Thirukkural.git
cd Thirukkural
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create the local SQLite database (only needed once, or after pulling schema
changes):

```bash
flask --app app init-db
```

Run the dev server:

```bash
python app.py
```

Open **http://127.0.0.1:5000**. Set `PORT` to run on a different port, and
`FLASK_DEBUG=1` to enable the reloader/debugger.

## Environment variables

All variables are optional for local development — the app falls back to
SQLite and logs OTP codes to the console instead of sending SMS.

| Variable | Purpose | Required for |
|---|---|---|
| `SECRET_KEY` | Flask session signing key | Production |
| `DATABASE_URL` | SQLAlchemy database URL (Postgres in production) | Production |
| `PORT` | Port the app listens on | Optional (default `5000`) |
| `FLASK_DEBUG` | Set to `1` to enable debug/reload mode | Local dev only |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth login | "Continue with Google" |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_FROM` | Sending real SMS OTPs | Phone login in production |

## Routes

| Route | Method | Description |
|---|---|---|
| `/` | GET | Landing page — pick a paal |
| `/part/<paal>` | GET | Paginated kural list for a paal, supports `?page=`, `?search=` |
| `/speak` | POST | `{text, key}` → generates/serves cached TTS audio |
| `/login`, `/signup`, `/logout` | GET/POST | Email + password auth |
| `/auth/phone`, `/auth/phone/verify` | POST | Phone OTP login |
| `/auth/google`, `/auth/google/callback` | GET | Google OAuth login |
| `/profile`, `/settings` | GET | Account pages (login required) |
| `/api/auth/*` | POST/GET | JSON equivalents of the auth routes above |

## Deploying (Render)

Already deployed at https://thirukkural-evaz.onrender.com — a `thirukkural`
web service (free plan) and a `thirukkural-db` Postgres database (free plan,
**expires 2026-10-09 unless upgraded**), both auto-deploying from `main`.

To set this up from scratch, the app ships with a `Procfile` and `start.sh`
for Render (or any Heroku-style host):

1. Push this repo to GitHub.
2. In Render, create a new **Web Service** from the repo.
   - Build command: `pip install -r requirements.txt`
   - Start command: `./start.sh`
3. Add a PostgreSQL database in Render and copy its connection string.
4. Set environment variables on the web service:
   - `SECRET_KEY` — any long random value
   - `DATABASE_URL` — the Postgres connection string from step 3
   - Optionally `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` (set the OAuth
     redirect URI to `https://<your-domain>/auth/google/callback`)
   - Optionally `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_FROM`
5. Deploy. `start.sh` runs `flask init-db` before starting Gunicorn, so
   tables are created automatically on first boot.

**Do not use SQLite in production** — most cloud filesystems are ephemeral,
so `app.db` (and any accounts in it) can vanish on restart or redeploy.
Always set `DATABASE_URL` to a managed Postgres instance in production.

## Data sources

- `data/thirukkural.json` — kural text and English translation/explanation.
- `data/thirukkural_meanings.json` — Tamil commentary from five classical
  commentators, merged into each kural at startup as `explanation_ta`.
- `data/detail.json` — the paal → iyal (இயல்) → chapter (அதிகாரம்) hierarchy,
  used to label each page with its chapter and to compute page ranges.
