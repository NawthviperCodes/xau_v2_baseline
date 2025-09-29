# backend/app.py
import os
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Flask, request, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from flask_cors import CORS

# Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("SIGNALS_DB", os.path.join(BASE_DIR, "signals.db"))
SECRET_KEY = os.environ.get("FLASK_SECRET", "change_this_secret_in_prod")
API_PUBLISH_KEY = os.environ.get("API_PUBLISH_KEY", "bot_publish_key_change_me")
JWT_SECRET = os.environ.get("JWT_SECRET", "jwt_secret_change_me")
TRIAL_DAYS = int(os.environ.get("TRIAL_DAYS", "5"))

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + DB_PATH
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = SECRET_KEY

db = SQLAlchemy(app)
CORS(app,
     resources={r"/*": {"origins": ["http://localhost:5500", "http://127.0.0.1:5500"]}},
     supports_credentials=True)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(320), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    trial_start = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    def trial_active(self):
        return datetime.now(timezone.utc) < (self.trial_start + timedelta(days=TRIAL_DAYS))

class Signal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(32), nullable=False)
    side = db.Column(db.String(8), nullable=False)  # buy / sell
    entry = db.Column(db.Float, nullable=False)
    confidence = db.Column(db.Float, nullable=True)
    strategy = db.Column(db.String(64), nullable=True)
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    meta = db.Column(db.Text, nullable=True)

# Utility / Auth
def create_db():
    db.create_all()

def generate_token(user_id, expires_hours=720):
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(hours=expires_hours),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("sub")
    except Exception:
        return None

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = auth.split(" ", 1)[1]
        user_id = verify_token(token)
        if not user_id:
            return jsonify({"error": "Invalid or expired token"}), 401
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        g.current_user = user
        return f(*args, **kwargs)
    return decorated

# Routes
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/register", methods=["POST"])
def register():
    data = request.json or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    if not email or not password:
        return jsonify({"error": "email and password required"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "email already registered"}), 409
    user = User(email=email, password_hash=generate_password_hash(password), trial_start=datetime.now(timezone.utc))
    db.session.add(user)
    db.session.commit()
    token = generate_token(user.id)
    return jsonify({"message": "registered", "token": token, "trial_expires": (user.trial_start + timedelta(days=TRIAL_DAYS)).isoformat()})

@app.route("/login", methods=["POST"])
def login():
    data = request.json or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    if not email or not password:
        return jsonify({"error": "email and password required"}), 400
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "invalid credentials"}), 401
    token = generate_token(user.id)
    return jsonify({"message": "ok", "token": token, "trial_expires": (user.trial_start + timedelta(days=TRIAL_DAYS)).isoformat()})

@app.route("/api/signal", methods=["POST"])
def ingest_signal():
    """
    Endpoint the bot uses to publish signals.
    Requires header: X-API-KEY: <API_PUBLISH_KEY>
    """
    key = request.headers.get("X-API-KEY", "")
    if not key or key != API_PUBLISH_KEY:
        return jsonify({"error": "invalid api key"}), 401
    data = request.json or {}
    required = ("symbol", "side", "entry")
    for r in required:
        if r not in data:
            return jsonify({"error": f"missing {r} field"}), 400
    try:
        s = Signal(
            symbol=str(data["symbol"]).upper(),
            side=str(data["side"]).lower(),
            entry=float(data["entry"]),
            confidence=float(data.get("confidence", 0.0)) if data.get("confidence") is not None else None,
            strategy=data.get("strategy"),
            meta=str(data.get("meta")) if data.get("meta") is not None else None,
            timestamp=datetime.now(timezone.utc)
        )
        db.session.add(s)
        db.session.commit()
        return jsonify({"message": "signal stored", "id": s.id}), 201
    except Exception as e:
        return jsonify({"error": f"failed to store signal: {e}"}), 500

@app.route("/signals", methods=["GET"])
@login_required
def get_signals():
    # Check trial
    user = g.current_user
    if not user.trial_active():
        return jsonify({"error": "trial_expired", "trial_expires": (user.trial_start + timedelta(days=TRIAL_DAYS)).isoformat()}), 402

    limit = int(request.args.get("limit", 50))
    q = Signal.query.order_by(Signal.timestamp.desc()).limit(min(limit, 200))
    out = []
    for s in q:
        out.append({
            "id": s.id,
            "symbol": s.symbol,
            "side": s.side,
            "entry": s.entry,
            "confidence": s.confidence,
            "strategy": s.strategy,
            "meta": s.meta,
            "time": s.timestamp.isoformat()
        })
    return jsonify({"signals": out})

@app.route("/me", methods=["GET"])
@login_required
def me():
    user = g.current_user
    return jsonify({
        "email": user.email,
        "trial_expires": (user.trial_start + timedelta(days=TRIAL_DAYS)).isoformat(),
        "trial_active": user.trial_active()
    })

# Admin helper (development) - reset DB
@app.route("/admin/reset-db", methods=["POST"])
def admin_reset():
    """
    WARNING: Development helper to re-create DB. Remove / protect in production.
    """
    secret = request.args.get("secret")
    if secret != "dev-reset-please-change":
        return jsonify({"error": "forbidden"}), 403
    db.drop_all()
    db.create_all()
    return jsonify({"message": "db reset"}), 200

if __name__ == "__main__":
    # Create DB if missing, inside the app context
    if not os.path.exists(DB_PATH):
        with app.app_context():
            create_db()
            print("DB created at", DB_PATH)

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)
