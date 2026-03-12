# 💰 Expense Tracker

A daily expense tracker built with **Flask + PostgreSQL**, ready to deploy online.

## Tech Stack

| Layer     | Technology                          |
|-----------|-------------------------------------|
| Backend   | Python 3 + Flask                    |
| Database  | PostgreSQL (psycopg2)               |
| Server    | Gunicorn (production WSGI)          |
| Frontend  | HTML5 + CSS3 + Vanilla JavaScript   |
| Deploy    | Render (free tier)                  |

---

## Project Structure

```
expense-tracker/
├── app.py                  # Flask app + REST API
├── requirements.txt        # Python dependencies
├── Procfile                # Tells Render/Heroku how to start the app
├── render.yaml             # One-click Render deploy config
├── .env.example            # Template for local environment variables
├── .gitignore
├── templates/
│   └── index.html
└── static/
    ├── css/style.css
    └── js/app.js
```

---

## API Endpoints

| Method | Endpoint                        | Description                  |
|--------|---------------------------------|------------------------------|
| GET    | `/api/expenses?month=YYYY-MM`   | List expenses for a month    |
| POST   | `/api/expenses`                 | Add a new expense            |
| DELETE | `/api/expenses/<id>`            | Delete an expense            |
| GET    | `/api/summary?month=YYYY-MM`    | Monthly stats + weekly data  |

---

## 🖥️ Local Development

### 1. Install PostgreSQL

Make sure PostgreSQL is running locally, then create a database:

```bash
psql -U postgres
CREATE DATABASE expenses_db;
CREATE USER expenses_user WITH PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE expenses_db TO expenses_user;
\q
```

### 2. Set up environment

```bash
cp .env.example .env
# Edit .env and fill in your DATABASE_URL
```

`.env` contents:
```
DATABASE_URL=postgresql://expenses_user:yourpassword@localhost:5432/expenses_db
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run

```bash
python app.py
```

Open → http://127.0.0.1:5000

---

## 🚀 Deploy to Render (Free)

### Option A — One-click with render.yaml (easiest)

1. Push this folder to a **GitHub repo**
2. Go to [render.com](https://render.com) → **New** → **Blueprint**
3. Connect your GitHub repo
4. Render reads `render.yaml` and automatically creates:
   - A **Web Service** (Flask app via Gunicorn)
   - A **PostgreSQL database** (free tier)
   - Injects `DATABASE_URL` into your app automatically
5. Click **Apply** → your app is live in ~2 minutes!

### Option B — Manual setup

1. Push to GitHub
2. **Render** → New → **PostgreSQL** → create free DB → copy the **Internal Database URL**
3. **Render** → New → **Web Service** → connect your repo
   - Build command:  `pip install -r requirements.txt`
   - Start command:  `gunicorn app:app`
   - Add env var:    `DATABASE_URL` = (paste the Internal Database URL)
4. Deploy!

---

## Features

- 📅 Month navigation (‹ / ›) — browse any past month
- 🗂️ 7 categories with icons (Food, Transport, Shopping, Health, Fun, Bills, Other)
- 📋 List view — grouped by date, filterable by category
- 📊 Summary view — 4 stat cards, interactive SVG pie charts (by category + by week), bar breakdown
- 🗑️ Delete expenses on hover
- 💾 All data stored in PostgreSQL (persists across deploys)
