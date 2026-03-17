import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

# ── DATABASE ──────────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ── LOGIN MANAGER ─────────────────────────────────────────────────────────────
login_manager = LoginManager(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
        if row:
            return User(row["id"], row["username"])
        return None
    finally:
        conn.close()

# ── DB HELPERS ────────────────────────────────────────────────────────────────
def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id       SERIAL PRIMARY KEY,
                    username VARCHAR(80) UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id         SERIAL PRIMARY KEY,
                    user_id    INT REFERENCES users(id) ON DELETE CASCADE,
                    amount     NUMERIC(10, 2) NOT NULL,
                    category   VARCHAR(50)    NOT NULL,
                    note       TEXT           NOT NULL,
                    date       DATE           NOT NULL,
                    created_at TIMESTAMPTZ    DEFAULT NOW()
                )
            """)
        conn.commit()
        print("✅ Database initialised")
    finally:
        conn.close()

if DATABASE_URL:
    try:
        init_db()
    except Exception as e:
        print(f"⚠️  init_db failed: {e}")

# ── AUTH ROUTES ───────────────────────────────────────────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            return render_template("register.html", error="All fields required")
        if len(password) < 6:
            return render_template("register.html", error="Password must be at least 6 characters")
        hashed = generate_password_hash(password)
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed))
            conn.commit()
            return redirect(url_for("login"))
        except Exception:
            conn.rollback()
            return render_template("register.html", error="Username already taken")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, username, password FROM users WHERE username = %s", (username,))
                row = cur.fetchone()
        finally:
            conn.close()
        if row and check_password_hash(row["password"], password):
            login_user(User(row["id"], row["username"]))
            return redirect(url_for("index"))
        return render_template("login.html", error="Wrong username or password")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ── MAIN ROUTE ────────────────────────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    return render_template("index.html", username=current_user.username)

# ── API: EXPENSES ─────────────────────────────────────────────────────────────
@app.route("/api/expenses", methods=["GET"])
@login_required
def get_expenses():
    month = request.args.get("month")
    conn = get_db()
    try:
        with conn.cursor() as cur:
            if month:
                cur.execute(
                    """SELECT id, amount::float, category, note,
                              TO_CHAR(date, 'YYYY-MM-DD') AS date
                       FROM expenses
                       WHERE TO_CHAR(date, 'YYYY-MM') = %s AND user_id = %s
                       ORDER BY date DESC, id DESC""",
                    (month, current_user.id)
                )
            else:
                cur.execute(
                    """SELECT id, amount::float, category, note,
                              TO_CHAR(date, 'YYYY-MM-DD') AS date
                       FROM expenses WHERE user_id = %s
                       ORDER BY date DESC, id DESC""",
                    (current_user.id,)
                )
            rows = cur.fetchall()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route("/api/expenses", methods=["POST"])
@login_required
def add_expense():
    data = request.get_json()
    try:
        amount   = float(data.get("amount", 0))
        category = data.get("category", "other")
        note     = data.get("note", "").strip() or category.title()
        date     = data.get("date") or datetime.today().strftime("%Y-%m-%d")
        if amount <= 0:
            return jsonify({"error": "Amount must be positive"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid data"}), 400
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO expenses (user_id, amount, category, note, date)
                   VALUES (%s, %s, %s, %s, %s)
                   RETURNING id, amount::float, category, note,
                             TO_CHAR(date, 'YYYY-MM-DD') AS date""",
                (current_user.id, amount, category, note, date)
            )
            row = cur.fetchone()
        conn.commit()
        return jsonify(dict(row)), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
@login_required
def delete_expense(expense_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM expenses WHERE id = %s AND user_id = %s", (expense_id, current_user.id))
        conn.commit()
        return jsonify({"deleted": expense_id})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route("/api/expenses/<int:expense_id>", methods=["PUT"])
@login_required
def edit_expense(expense_id):
    data = request.get_json()
    try:
        amount   = float(data.get("amount", 0))
        category = data.get("category", "other")
        note     = data.get("note", "").strip() or category.title()
        date     = data.get("date") or datetime.today().strftime("%Y-%m-%d")
        if amount <= 0:
            return jsonify({"error": "Amount must be positive"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid data"}), 400
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE expenses SET amount=%s, category=%s, note=%s, date=%s
                   WHERE id=%s AND user_id=%s
                   RETURNING id, amount::float, category, note,
                             TO_CHAR(date, 'YYYY-MM-DD') AS date""",
                (amount, category, note, date, expense_id, current_user.id)
            )
            row = cur.fetchone()
        conn.commit()
        if not row:
            return jsonify({"error": "Not found"}), 404
        return jsonify(dict(row))
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route("/api/summary", methods=["GET"])
@login_required
def get_summary():
    month = request.args.get("month")
    conn = get_db()
    try:
        with conn.cursor() as cur:
            if month:
                cur.execute(
                    """SELECT category, SUM(amount)::float AS total
                       FROM expenses WHERE TO_CHAR(date, 'YYYY-MM') = %s AND user_id = %s
                       GROUP BY category""", (month, current_user.id)
                )
            else:
                cur.execute(
                    "SELECT category, SUM(amount)::float AS total FROM expenses WHERE user_id=%s GROUP BY category",
                    (current_user.id,)
                )
            cat_rows = cur.fetchall()

            if month:
                cur.execute(
                    "SELECT COALESCE(SUM(amount),0)::float AS t FROM expenses WHERE TO_CHAR(date,'YYYY-MM')=%s AND user_id=%s",
                    (month, current_user.id)
                )
            else:
                cur.execute("SELECT COALESCE(SUM(amount),0)::float AS t FROM expenses WHERE user_id=%s", (current_user.id,))
            month_total = cur.fetchone()["t"]

            cur.execute("SELECT COALESCE(SUM(amount),0)::float AS t FROM expenses WHERE user_id=%s", (current_user.id,))
            all_time = cur.fetchone()["t"]

            if month:
                cur.execute(
                    "SELECT COUNT(*) AS c FROM expenses WHERE TO_CHAR(date,'YYYY-MM')=%s AND user_id=%s",
                    (month, current_user.id)
                )
            else:
                cur.execute("SELECT COUNT(*) AS c FROM expenses WHERE user_id=%s", (current_user.id,))
            count = cur.fetchone()["c"]

            if month:
                cur.execute(
                    """SELECT CEIL(EXTRACT(DAY FROM date)/7.0)::int AS week_num,
                              SUM(amount)::float AS total
                       FROM expenses WHERE TO_CHAR(date,'YYYY-MM')=%s AND user_id=%s
                       GROUP BY week_num ORDER BY week_num""", (month, current_user.id)
                )
                weekly = cur.fetchall()
            else:
                weekly = []

        return jsonify({
            "categories": [dict(r) for r in cat_rows],
            "total":      month_total,
            "all_time":   all_time,
            "count":      count,
            "weekly":     [dict(r) for r in weekly],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route("/api/health")
def health():
    try:
        conn = get_db()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀  Running on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
