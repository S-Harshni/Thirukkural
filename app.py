# app.py
from __future__ import annotations

import hashlib
import json
import math
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from authlib.integrations.flask_client import OAuth
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from gtts import gTTS
from werkzeug.security import check_password_hash, generate_password_hash

# -----------------------------
# App + Paths
# -----------------------------

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "data" / "thirukkural.json"
DETAIL_FILE = BASE_DIR / "data" / "detail.json"
MEANINGS_FILE = BASE_DIR / "data" / "thirukkural_meanings.json"
STATIC_DIR = BASE_DIR / "static"
AUDIO_DIR = STATIC_DIR / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder=str(STATIC_DIR), template_folder="templates")


def _normalize_db_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = _normalize_db_url(
    os.environ.get("DATABASE_URL", f"sqlite:///{(BASE_DIR / 'app.db')}")
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = "login"
oauth = OAuth(app)

# -----------------------------
# Pagination Settings
# -----------------------------

KURALS_PER_PAGE = 10
PAGE_JUMP = 10  # Prev/Next arrow jump
PAGER_WINDOW = 10  # How many page numbers to display at once
TAMIL_MEANING_FIELDS = (
    "salaman_papa",
    "mu_varadha",
    "mu_karunanidhi",
    "v_munusami",
    "mani_kudavar",
    "pari_melakar",
)

# -----------------------------
# Data Loading + Indexes
# -----------------------------


def _load_kurals(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload["kural"]


def _build_tamil_meaning_lookup(path: Path) -> dict[int, str]:
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, dict):
        return {}

    meaning_by_no: dict[int, str] = {}
    for raw_no, item in payload.items():
        try:
            kural_no = int(raw_no)
        except (TypeError, ValueError):
            continue

        if not isinstance(item, dict):
            continue

        for field in TAMIL_MEANING_FIELDS:
            value = item.get(field)
            if isinstance(value, str) and value.strip():
                meaning_by_no[kural_no] = value.strip()
                break

    return meaning_by_no


def _build_kural_detail_lookup(path: Path) -> dict[int, dict]:
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, list):
        payload = payload[0] if payload else {}

    section = payload.get("section") or {}
    paal_label_tamil = (section.get("tamil") or "பால்").strip()
    detail_by_no: dict[int, dict] = {}

    for paal in section.get("detail", []):
        paal_name = (paal.get("name") or "").strip()
        chapter_group = paal.get("chapterGroup") or {}
        iyal_label_tamil = (chapter_group.get("tamil") or "இயல்").strip()

        for iyal in chapter_group.get("detail", []):
            iyal_name = (iyal.get("name") or "").strip()
            chapters = iyal.get("chapters") or {}
            chapter_label_tamil = (chapters.get("tamil") or "அதிகாரம்").strip()

            for chapter in chapters.get("detail", []):
                start = chapter.get("start")
                end = chapter.get("end")
                if not isinstance(start, int) or not isinstance(end, int):
                    continue

                meta = {
                    "paal_label_tamil": paal_label_tamil,
                    "paal_name": paal_name,
                    "paal_no": paal.get("number"),
                    "iyal_label_tamil": iyal_label_tamil,
                    "iyal_name": iyal_name,
                    "iyal_no": iyal.get("number"),
                    "chapter_label_tamil": chapter_label_tamil,
                    "chapter_name": (chapter.get("name") or "").strip(),
                    "chapter_no": chapter.get("number"),
                    "chapter_start": start,
                    "chapter_end": end,
                }

                for kural_no in range(start, end + 1):
                    detail_by_no[kural_no] = meta.copy()

    return detail_by_no


def _merge_detail_metadata(kurals: list[dict], detail_by_no: dict[int, dict]) -> None:
    for kural in kurals:
        detail = detail_by_no.get(kural.get("Number"))
        if not detail:
            continue

        kural["paal"] = detail.get("paal_name") or kural.get("paal") or kural.get("Paal")
        kural["chapter_no"] = detail.get("chapter_no")
        kural["chapter_name"] = detail.get("chapter_name") or ""
        kural["paal_label_tamil"] = detail.get("paal_label_tamil") or "பால்"
        kural["paal_name"] = detail.get("paal_name") or ""
        kural["paal_no"] = detail.get("paal_no")
        kural["iyal_label_tamil"] = detail.get("iyal_label_tamil") or "இயல்"
        kural["iyal_name"] = detail.get("iyal_name") or ""
        kural["iyal_no"] = detail.get("iyal_no")
        kural["chapter_label_tamil"] = detail.get("chapter_label_tamil") or "அதிகாரம்"
        kural["chapter_start"] = detail.get("chapter_start")
        kural["chapter_end"] = detail.get("chapter_end")


def _merge_tamil_meanings(kurals: list[dict], meaning_by_no: dict[int, str]) -> None:
    for kural in kurals:
        tamil_meaning = meaning_by_no.get(kural.get("Number"))
        if tamil_meaning:
            kural["explanation_ta"] = tamil_meaning


ALL_KURALS = _load_kurals(DATA_FILE)
KURAL_DETAILS_BY_NO = _build_kural_detail_lookup(DETAIL_FILE)
KURAL_TAMIL_MEANINGS_BY_NO = _build_tamil_meaning_lookup(MEANINGS_FILE)
_merge_detail_metadata(ALL_KURALS, KURAL_DETAILS_BY_NO)
_merge_tamil_meanings(ALL_KURALS, KURAL_TAMIL_MEANINGS_BY_NO)
INDEX_BY_NO: dict[int, dict] = {k["Number"]: k for k in ALL_KURALS}

# Preserve first-seen order of paals from the dataset.
PAALS: list[str] = []
for k in ALL_KURALS:
    p = k.get("paal") or k.get("Paal")
    if p and p not in PAALS:
        PAALS.append(p)

if not PAALS:
    PAALS = ["அறத்துப்பால்", "பொருட்பால்", "காமத்துப்பால்"]

# Global start page for each paal (1-indexed global pages across the whole book)
PAAL_START_PAGE: dict[str, int] = {
    "அறத்துப்பால்": 1,
    "பொருட்பால்": 39,
    "காமத்துப்பால்": 109,
}

# Fast lookup: paal -> list of kurals
KURALS_BY_PAAL: dict[str, list[dict]] = {p: [] for p in PAALS}
for k in ALL_KURALS:
    p = k.get("paal") or k.get("Paal")
    if p in KURALS_BY_PAAL:
        KURALS_BY_PAAL[p].append(k)


def _paginate(items: list[dict], page: int) -> tuple[list[dict], int]:
    total = len(items)
    total_pages = max(1, math.ceil(total / KURALS_PER_PAGE))
    page = max(1, min(page, total_pages))
    start = (page - 1) * KURALS_PER_PAGE
    end = start + KURALS_PER_PAGE
    return items[start:end], total_pages


def _page_window_within_paal(global_page: int, start_global: int, end_global: int) -> tuple[int, int]:
    """Return a PAGER_WINDOW-sized window of global page numbers, clamped to a paal range."""
    window_start = start_global + ((global_page - start_global) // PAGER_WINDOW) * PAGER_WINDOW
    window_end = min(window_start + PAGER_WINDOW - 1, end_global)
    return window_start, window_end


def _build_paal_meta() -> dict[str, dict]:
    """Compute global page ranges per paal based on dataset sizes + configured start pages."""
    meta: dict[str, dict] = {}
    inferred_next_start = 1

    for idx, paal in enumerate(PAALS):
        items = KURALS_BY_PAAL.get(paal, [])
        count = len(items)
        pages = max(1, math.ceil(len(items) / KURALS_PER_PAGE))

        start = PAAL_START_PAGE.get(paal) or inferred_next_start
        end = start + pages - 1
        inferred_next_start = end + 1

        meta[paal] = {"index": idx, "start": start, "end": end, "pages": pages, "count": count}

    return meta


PAAL_META = _build_paal_meta()


def _safe_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except Exception:
        return default


# -----------------------------
# Auth Models + Helpers
# -----------------------------


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, index=True)
    password_hash = db.Column(db.String(255))
    name = db.Column(db.String(120))
    phone = db.Column(db.String(32), unique=True, index=True)
    phone_verified = db.Column(db.Boolean, default=False)
    oauth_provider = db.Column(db.String(50))
    oauth_sub = db.Column(db.String(255), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)


class PhoneOTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(32), index=True, nullable=False)
    code_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


@login_manager.user_loader
def load_user(user_id: str):
    if not user_id:
        return None
    return db.session.get(User, int(user_id))


@app.context_processor
def inject_auth():
    return {"logged_in": current_user.is_authenticated, "current_user": current_user}


def _generate_otp() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def _send_sms_code(phone: str, code: str) -> tuple[bool, str | None]:
    """Send SMS via Twilio if configured. Otherwise log to console."""
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    sender = os.environ.get("TWILIO_FROM")

    if sid and token and sender:
        try:
            import requests

            url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
            resp = requests.post(
                url,
                data={"From": sender, "To": phone, "Body": f"Your login code is {code}"},
                auth=(sid, token),
                timeout=10,
            )
            if resp.status_code >= 400:
                return False, f"Twilio error: {resp.text}"
            return True, None
        except Exception as exc:
            return False, f"SMS failed: {exc}"

    app.logger.info("SMS DEV MODE code for %s: %s", phone, code)
    return True, "dev"


@app.cli.command("init-db")
def init_db_command():
    """Create database tables without migrations (dev helper)."""
    db.create_all()
    print("Database tables created.")


# Configure Google OAuth if credentials are available.
if os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET"):
    oauth.register(
        name="google",
        client_id=os.environ.get("GOOGLE_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

# Auto-create tables for local SQLite (keeps dev setup simple).
if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///"):
    with app.app_context():
        db.create_all()


# -----------------------------
# Routes
# -----------------------------


@app.route("/")
def index():
    return render_template(
        "landing.html",
        paals=PAALS,
        paal_start={p: PAAL_META[p]["start"] for p in PAALS},
        paal_meta=PAAL_META,
    )


# -----------------------------
# Auth Pages
# -----------------------------


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        if not email or not password:
            flash("Email and password are required.", "error")
        else:
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                login_user(user)
                flash("Logged in successfully.", "success")
                return redirect(url_for("index"))
            flash("Invalid credentials.", "error")

    return render_template("login.html", pending_phone=session.get("pending_phone"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""

        if not email or not password:
            flash("Email and password are required.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
        else:
            user = User(email=email, name=name)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Account created successfully.", "success")
            return redirect(url_for("index"))

    return render_template("signup.html")


@app.route("/logout")
def logout():
    logout_user()
    flash("Logged out.", "success")
    return redirect(url_for("index"))


@app.route("/profile")
def profile():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    return render_template("profile.html")


@app.route("/settings")
def settings():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    return render_template("settings.html")


@app.route("/auth/google")
def google_login():
    if not (os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET")):
        flash("Google login is not configured. Add GOOGLE_CLIENT_ID/SECRET.", "error")
        return redirect(url_for("login"))
    redirect_uri = url_for("google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@app.route("/auth/google/callback")
def google_callback():
    if not (os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET")):
        flash("Google login is not configured.", "error")
        return redirect(url_for("login"))
    token = oauth.google.authorize_access_token()
    userinfo = None
    try:
        userinfo = oauth.google.parse_id_token(token)
    except Exception:
        try:
            resp = oauth.google.get("userinfo")
            if resp:
                userinfo = resp.json()
        except Exception:
            userinfo = None
    if not userinfo:
        flash("Unable to fetch Google profile.", "error")
        return redirect(url_for("login"))

    email = (userinfo.get("email") or "").lower()
    sub = userinfo.get("sub")
    name = userinfo.get("name") or ""

    user = None
    if sub:
        user = User.query.filter_by(oauth_provider="google", oauth_sub=sub).first()
    if not user and email:
        user = User.query.filter_by(email=email).first()

    if not user:
        user = User(email=email, name=name, oauth_provider="google", oauth_sub=sub)
        db.session.add(user)
        db.session.commit()
    else:
        if not user.oauth_provider:
            user.oauth_provider = "google"
            user.oauth_sub = sub
            db.session.commit()

    login_user(user)
    flash("Logged in with Google.", "success")
    return redirect(url_for("index"))


@app.route("/auth/phone", methods=["POST"])
def phone_start():
    phone = (request.form.get("phone") or "").strip()
    if not phone:
        flash("Phone number is required.", "error")
        return redirect(url_for("login"))

    code = _generate_otp()
    otp = PhoneOTP(
        phone=phone,
        code_hash=generate_password_hash(code),
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    )
    db.session.add(otp)
    db.session.commit()

    ok, info = _send_sms_code(phone, code)
    if not ok:
        flash(f"Unable to send SMS. {info}", "error")
        return redirect(url_for("login"))

    session["pending_phone"] = phone
    flash("OTP sent. Check your phone.", "success")
    if info == "dev":
        flash("Dev mode: check server logs for the OTP code.", "info")
    return redirect(url_for("login"))


@app.route("/auth/phone/verify", methods=["POST"])
def phone_verify():
    phone = (request.form.get("phone") or session.get("pending_phone") or "").strip()
    code = (request.form.get("code") or "").strip()
    if not phone or not code:
        flash("Phone and code are required.", "error")
        return redirect(url_for("login"))

    otp = (
        PhoneOTP.query.filter_by(phone=phone, used=False)
        .order_by(PhoneOTP.created_at.desc())
        .first()
    )

    if not otp or otp.expires_at < datetime.utcnow():
        flash("OTP expired. Please request again.", "error")
        return redirect(url_for("login"))

    if not check_password_hash(otp.code_hash, code):
        flash("Invalid OTP.", "error")
        return redirect(url_for("login"))

    otp.used = True
    user = User.query.filter_by(phone=phone).first()
    if not user:
        user = User(phone=phone, phone_verified=True)
        db.session.add(user)
    else:
        user.phone_verified = True
    db.session.commit()

    login_user(user)
    session.pop("pending_phone", None)
    flash("Logged in with phone.", "success")
    return redirect(url_for("index"))


# -----------------------------
# Auth APIs (JSON)
# -----------------------------


@app.route("/api/auth/signup", methods=["POST"])
def api_signup():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    name = (body.get("name") or "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400

    user = User(email=email, name=name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return jsonify({"ok": True, "user": {"id": user.id, "email": user.email}})


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401
    login_user(user)
    return jsonify({"ok": True, "user": {"id": user.id, "email": user.email}})


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    logout_user()
    return jsonify({"ok": True})


@app.route("/api/auth/phone/start", methods=["POST"])
def api_phone_start():
    body = request.get_json(silent=True) or {}
    phone = (body.get("phone") or "").strip()
    if not phone:
        return jsonify({"error": "Phone required"}), 400
    code = _generate_otp()
    otp = PhoneOTP(
        phone=phone,
        code_hash=generate_password_hash(code),
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    )
    db.session.add(otp)
    db.session.commit()
    ok, info = _send_sms_code(phone, code)
    if not ok:
        return jsonify({"error": "SMS send failed", "detail": info}), 400
    session["pending_phone"] = phone
    return jsonify({"ok": True, "mode": info or "sms"})


@app.route("/api/auth/phone/verify", methods=["POST"])
def api_phone_verify():
    body = request.get_json(silent=True) or {}
    phone = (body.get("phone") or session.get("pending_phone") or "").strip()
    code = (body.get("code") or "").strip()
    if not phone or not code:
        return jsonify({"error": "Phone and code required"}), 400
    otp = (
        PhoneOTP.query.filter_by(phone=phone, used=False)
        .order_by(PhoneOTP.created_at.desc())
        .first()
    )
    if not otp or otp.expires_at < datetime.utcnow():
        return jsonify({"error": "OTP expired"}), 400
    if not check_password_hash(otp.code_hash, code):
        return jsonify({"error": "Invalid OTP"}), 400
    otp.used = True
    user = User.query.filter_by(phone=phone).first()
    if not user:
        user = User(phone=phone, phone_verified=True)
        db.session.add(user)
    else:
        user.phone_verified = True
    db.session.commit()
    login_user(user)
    session.pop("pending_phone", None)
    return jsonify({"ok": True, "user": {"id": user.id}})


@app.route("/api/auth/me")
def api_me():
    if not current_user.is_authenticated:
        return jsonify({"user": None})
    return jsonify(
        {
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "name": current_user.name,
                "phone": current_user.phone,
            }
        }
    )




@app.route("/part/<paal>")
def part(paal: str):
    if paal not in PAAL_META:
        paal = PAALS[0]

    start_global = PAAL_META[paal]["start"]
    end_global = PAAL_META[paal]["end"]

    global_page = _safe_int(request.args.get("page"), start_global)
    global_page = max(start_global, min(global_page, end_global))
    local_page = (global_page - start_global) + 1

    # Support highlight from redirects.
    highlight = (request.args.get("highlight") or "").strip()

    search = (request.args.get("search") or "").strip()
    kurals_for_paal = KURALS_BY_PAAL[paal]

    if search.isdigit():
        num = int(search)

        # If the searched kural is inside this paal, jump to its local page.
        idx = next((i for i, k in enumerate(kurals_for_paal) if k["Number"] == num), None)
        if idx is not None:
            local_page = (idx // KURALS_PER_PAGE) + 1
            global_page = start_global + local_page - 1
            highlight = str(num)
        else:
            # Otherwise, redirect to the paal that owns it.
            k_global = INDEX_BY_NO.get(num)
            if k_global:
                redirect_paal = k_global.get("paal") or k_global.get("Paal")
                if redirect_paal in KURALS_BY_PAAL:
                    target_list = KURALS_BY_PAAL[redirect_paal]
                    idx2 = next((i for i, k in enumerate(target_list) if k["Number"] == num), None)
                    if idx2 is not None:
                        return redirect(
                            url_for(
                                "part",
                                paal=redirect_paal,
                                page=(PAAL_START_PAGE.get(redirect_paal, PAAL_META[redirect_paal]["start"]) + (idx2 // KURALS_PER_PAGE)),
                                highlight=num,
                                search=num,  # lets the client know it came from search
                            )
                        )

    page_items, _total_pages_local = _paginate(kurals_for_paal, local_page)
    first_item = page_items[0] if page_items else {}
    raw_chapter_no = first_item.get("chapter_no")
    if isinstance(raw_chapter_no, str):
        raw_chapter_no = raw_chapter_no.strip()
    chapter_no = raw_chapter_no if raw_chapter_no not in (None, "") else None
    chapter_name = (first_item.get("chapter_name") or "").strip()
    chapter_label = (first_item.get("chapter_label_tamil") or "அதிகாரம்").strip()

    if not chapter_name:
        chapter_name = "—"
    page_start, page_end = _page_window_within_paal(global_page, start_global, end_global)

    # Prev/Next jump within paal; on boundary jump to neighboring paal.
    prev_url = None
    next_url = None
    idx_paal = PAAL_META[paal]["index"]

    if global_page > start_global:
        prev_url = url_for("part", paal=paal, page=max(start_global, global_page - PAGE_JUMP))
    elif idx_paal > 0:
        prev_paal = PAALS[idx_paal - 1]
        prev_url = url_for("part", paal=prev_paal, page=PAAL_META[prev_paal]["end"])

    if global_page < end_global:
        next_url = url_for("part", paal=paal, page=min(end_global, global_page + PAGE_JUMP))
    elif idx_paal < len(PAALS) - 1:
        next_paal = PAALS[idx_paal + 1]
        next_url = url_for("part", paal=next_paal, page=PAAL_META[next_paal]["start"])

    return render_template(
        "part.html",
        paals=PAALS,
        paal_start={p: PAAL_META[p]["start"] for p in PAALS},
        current_paal=paal,
        paal_index=idx_paal,
        paal_count=len(PAALS),
        kurals=page_items,
        page=global_page,
        page_start=page_start,
        page_end=page_end,
        pager_window=PAGER_WINDOW,
        pager_count=(page_end - page_start + 1),
        prev_url=prev_url,
        next_url=next_url,
        highlight=highlight,
        chapter_no=chapter_no,
        chapter_name=chapter_name,
        chapter_label=chapter_label,
    )


@app.route("/speak", methods=["POST"])
def speak():
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()[:4000]
    key = body.get("key") or "temp"

    if not text:
        return jsonify({"error": "No text provided"}), 400

    safe_key = "".join(ch for ch in key if ch.isalnum() or ch in ("_", "-")) or "temp"
    text_hash = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    filename = AUDIO_DIR / f"{safe_key}_{text_hash}.mp3"

    # Cache by content so a previously generated English file is not reused for Tamil text.
    if filename.exists() and filename.stat().st_size > 0:
        return jsonify({"audio": f"/static/audio/{filename.name}"})

    try:
        gTTS(text=text, lang="ta").save(str(filename))
        return jsonify({"audio": f"/static/audio/{filename.name}"})
    except Exception as e:
        if filename.exists():
            filename.unlink(missing_ok=True)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
