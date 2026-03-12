import os
from flask import Flask, render_template, request, jsonify
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

app = Flask(__name__)

# ── DATABASE ──────────────────────────────────────────────────────────────────
# Render provides DATABASE_URL automatically when you attach a PostgreSQL db.
# For local dev, set DATABASE_URL in a .env file or your shell:
#   export DATABASE_URL="postgresql://user:password@localhost:5432/expenses_db"

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Render uses 'postgres://' but psycopg2 needs 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn


def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id         SERIAL PRIMARY KEY,
                    amount     NUMERIC(10, 2) NOT NULL,
                    category   VARCHAR(50)    NOT NULL,
                    note       TEXT           NOT NULL,
                    date       DATE           NOT NULL,
                    created_at TIMESTAMPTZ    DEFAULT NOW()
                )
            """)
        conn.commit()
    print("✅ Database initialised")


# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/expenses", methods=["GET"])
def get_expenses():
    month = request.args.get("month")   # YYYY-MM
    with get_db() as conn:
        with conn.cursor() as cur:
            if month:
                cur.execute(
                    """SELECT id, amount::float, category, note,
                              TO_CHAR(date, 'YYYY-MM-DD') AS date
                       FROM expenses
                       WHERE TO_CHAR(date, 'YYYY-MM') = %s
                       ORDER BY date DESC, id DESC""",
                    (month,)
                )
            else:
                cur.execute(
                    """SELECT id, amount::float, category, note,
                              TO_CHAR(date, 'YYYY-MM-DD') AS date
                       FROM expenses
                       ORDER BY date DESC, id DESC"""
                )
            rows = cur.fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/expenses", methods=["POST"])
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

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO expenses (amount, category, note, date)
                   VALUES (%s, %s, %s, %s)
                   RETURNING id, amount::float, category, note,
                             TO_CHAR(date, 'YYYY-MM-DD') AS date""",
                (amount, category, note, date)
            )
            row = cur.fetchone()
        conn.commit()
    return jsonify(dict(row)), 201


@app.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
        conn.commit()
    return jsonify({"deleted": expense_id})


@app.route("/api/summary", methods=["GET"])
def get_summary():
    month = request.args.get("month")   # YYYY-MM
    with get_db() as conn:
        with conn.cursor() as cur:
            # Category totals for selected month
            if month:
                cur.execute(
                    """SELECT category, SUM(amount)::float AS total
                       FROM expenses
                       WHERE TO_CHAR(date, 'YYYY-MM') = %s
                       GROUP BY category""",
                    (month,)
                )
            else:
                cur.execute(
                    "SELECT category, SUM(amount)::float AS total FROM expenses GROUP BY category"
                )
            cat_rows = cur.fetchall()

            # Month total
            if month:
                cur.execute(
                    "SELECT COALESCE(SUM(amount), 0)::float AS t FROM expenses WHERE TO_CHAR(date, 'YYYY-MM') = %s",
                    (month,)
                )
            else:
                cur.execute("SELECT COALESCE(SUM(amount), 0)::float AS t FROM expenses")
            month_total = cur.fetchone()["t"]

            # All-time total
            cur.execute("SELECT COALESCE(SUM(amount), 0)::float AS t FROM expenses")
            all_time = cur.fetchone()["t"]

            # Transaction count
            if month:
                cur.execute(
                    "SELECT COUNT(*) AS c FROM expenses WHERE TO_CHAR(date, 'YYYY-MM') = %s",
                    (month,)
                )
            else:
                cur.execute("SELECT COUNT(*) AS c FROM expenses")
            count = cur.fetchone()["c"]

            # Weekly breakdown  (week 1 = days 1-7, week 2 = 8-14, …)
            if month:
                cur.execute(
                    """SELECT
                           CEIL(EXTRACT(DAY FROM date) / 7.0)::int AS week_num,
                           SUM(amount)::float AS total
                       FROM expenses
                       WHERE TO_CHAR(date, 'YYYY-MM') = %s
                       GROUP BY week_num
                       ORDER BY week_num""",
                    (month,)
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


# ── ENTRY POINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀  Running on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
