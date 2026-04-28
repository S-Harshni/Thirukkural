Thirukkural Flask App
====================

Run:
  python app.py

Open in browser:
  http://127.0.0.1:5000/

Notes:
- Use the search box (top-right) to jump to a Kural number.
- Pagination uses global page numbers across the full book:
  - அறத்துப்பால்: pages 1–38
  - பொருட்பால்: pages 39–108
  - காமத்துப்பால்: pages 109–133
- Audio is generated via gTTS and cached under static/audio/.

Deploy on Render
----------------

This app is ready to deploy as a public Flask website.

1. Push this project to GitHub.
2. In Render, create a new Web Service from that GitHub repo.
3. Use these settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `./start.sh`
4. Add environment variables in Render:
   - `SECRET_KEY` = any long random value
   - `DATABASE_URL` = your PostgreSQL connection string
5. Create a PostgreSQL database in Render (or another managed Postgres provider) and copy its `DATABASE_URL` into the web service.
6. Deploy. Render will give you a public URL like `https://your-app.onrender.com`.

Important cloud notes
---------------------

- Do not use `app.db` / SQLite for production hosting. Cloud filesystems are often temporary, so user data can disappear after a restart or redeploy.
- `start.sh` runs `flask init-db` before starting Gunicorn so the tables are created on a fresh PostgreSQL database.
- If you use Google login, also set:
  - `GOOGLE_CLIENT_ID`
  - `GOOGLE_CLIENT_SECRET`
  - Google OAuth redirect URL: `https://your-domain/auth/google/callback`
- If you use phone OTP via Twilio, also set:
  - `TWILIO_ACCOUNT_SID`
  - `TWILIO_AUTH_TOKEN`
  - `TWILIO_FROM`
