# Fin-Tracker

A daily expense tracker built with Flask + PostgreSQL, deployed on Render.

🔗 **Live Demo** → [fin-tracker-m6iv.onrender.com](https://fin-tracker-m6iv.onrender.com)

## Tech Stack

| Layer    | Technology                        |
|----------|-----------------------------------|
| Backend  | Python 3 + Flask                  |
| Database | PostgreSQL (psycopg2)             |
| Server   | Gunicorn (production WSGI)        |
| Frontend | HTML5 + CSS3 + Vanilla JavaScript |
| Deploy   | Render (free tier)                |

## Features
- 📅 Browse expenses by month
- 🗂️ 7 categories — Food, Transport, Shopping, Health, Fun, Bills, Other
- 📋 List view grouped by date with category filters
- 📊 Summary view with pie charts and spending breakdown
- 🗑️ Delete expenses
- 💾 Data persists in PostgreSQL

## Project Structure
```
expense-tracker/
├── app.py
├── requirements.txt
├── Procfile
├── templates/index.html
└── static/
    ├── css/style.css
    └── js/app.js
```

## Run Locally
```bash
cp .env.example .env        # add your DATABASE_URL
pip install -r requirements.txt
python app.py               # open http://127.0.0.1:5000
```

## Deploy to Render
1. Push to GitHub
2. Create a **PostgreSQL** database on Render → copy the Internal Database URL
3. Create a **Web Service** → connect your repo
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn app:app`
   - Env var: `DATABASE_URL` = (Internal Database URL)
4. Done! 
