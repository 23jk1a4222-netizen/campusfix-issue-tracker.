# CampusFix — College Campus Issue Reporting and Tracking System

CampusFix is a Flask web app where students report campus maintenance problems and track their status. Administrators can review all reports, change priority, and update statuses.

## Features
- Student registration, login, and logout
- Secure password hashing
- Student-only complaint submission and personal complaint history
- Admin dashboard for all complaints
- Statuses: Pending, In Progress, Resolved
- Priorities: Low, Medium, High
- Search/filter-ready structured dashboard and summary counts
- Responsive Bootstrap interface
- SQLite locally; PostgreSQL recommended for deployed use

## Requirements
- Python 3.10+
- pip

## Run locally
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
# Optional: set a unique SECRET_KEY environment variable before running.
python app.py
```
Open http://127.0.0.1:5000

The database is created automatically on first run.

## Create an administrator account
For safety, public registration always creates a student account. After registering the account you intend to use as an administrator, open a Python shell in the project folder:

```bash
python
```

Then run:
```python
from app import app, db, User
with app.app_context():
    user = User.query.filter_by(email="your-email@example.com").first()
    user.role = "admin"
    db.session.commit()
```
Replace the email with the registered administrator email. Do not expose admin credentials or add a public admin-registration option.

## Deploy on Render
1. Push this project to a **public GitHub repository**.
2. In Render, create a new **PostgreSQL** database and copy its **Internal Database URL**.
3. Create a new **Web Service** connected to your repository.
4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn app:app`
6. Set environment variables:
   - `SECRET_KEY`: a long, random secret value
   - `DATABASE_URL`: the PostgreSQL Internal Database URL from Render
7. Deploy and open the URL Render provides.
8. Register an account, then promote the intended administrator account using a one-time shell/console command with the production database connection. Never expose an admin password in source code.

If using a different hosting provider, configure its persistent PostgreSQL URL and environment variables similarly.

## Important notes
- The app creates tables automatically, but production schema changes should use database migrations as the project grows.
- Use PostgreSQL for hosted data persistence. Do not rely on a local SQLite file on ephemeral hosting.
- This is a student project starter. Before real institutional use, add email verification, rate limiting, audit logs, secure image uploads, backups, and a formal privacy policy.
