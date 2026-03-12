import os
from flask import Flask, render_template, request, jsonify
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# ── DATABASE ──────────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_db():
    conn = get_db()
    try:
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
    finally:
        conn.close()


# Run init_db at startup — works with both Gunicorn and python app.py
if DATABASE_URL:
    try:
        init_db()
    except Exception as e:
        print(f"⚠️  init_db failed: {e}")


# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/expenses", methods=["GET"])
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
                       WHERE TO_CHAR(date, 'YYYY-MM') = %s
                       ORDER BY date DESC, id DESC""",
                    (month,)
                )
            else:
                cur.execute(
                    """SELECT id, amount::float, category, note,
                              TO_CHAR(date, 'YYYY-MM-DD') AS date
                       FROM expenses ORDER BY date DESC, id DESC"""
                )
            rows = cur.fetchall()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


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

    conn = get_db()
    try:
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
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
        conn.commit()
        return jsonify({"deleted": expense_id})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/summary", methods=["GET"])
def get_summary():
    month = request.args.get("month")
    conn = get_db()
    try:
        with conn.cursor() as cur:
            if month:
                cur.execute(
                    """SELECT category, SUM(amount)::float AS total
                       FROM expenses WHERE TO_CHAR(date, 'YYYY-MM') = %s
                       GROUP BY category""", (month,)
                )
            else:
                cur.execute("SELECT category, SUM(amount)::float AS total FROM expenses GROUP BY category")
            cat_rows = cur.fetchall()

            if month:
                cur.execute(
                    "SELECT COALESCE(SUM(amount),0)::float AS t FROM expenses WHERE TO_CHAR(date,'YYYY-MM')=%s",
                    (month,)
                )
            else:
                cur.execute("SELECT COALESCE(SUM(amount),0)::float AS t FROM expenses")
            month_total = cur.fetchone()["t"]

            cur.execute("SELECT COALESCE(SUM(amount),0)::float AS t FROM expenses")
            all_time = cur.fetchone()["t"]

            if month:
                cur.execute(
                    "SELECT COUNT(*) AS c FROM expenses WHERE TO_CHAR(date,'YYYY-MM')=%s", (month,)
                )
            else:
                cur.execute("SELECT COUNT(*) AS c FROM expenses")
            count = cur.fetchone()["c"]

            if month:
                cur.execute(
                    """SELECT CEIL(EXTRACT(DAY FROM date)/7.0)::int AS week_num,
                              SUM(amount)::float AS total
                       FROM expenses WHERE TO_CHAR(date,'YYYY-MM')=%s
                       GROUP BY week_num ORDER BY week_num""", (month,)
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


# ── HEALTH CHECK ──────────────────────────────────────────────────────────────
@app.route("/api/health")
def health():
    try:
        conn = get_db()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500


# ── ENTRY POINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀  Running on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
