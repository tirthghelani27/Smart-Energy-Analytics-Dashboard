<h1 align="center">
  ⚡ Smart Energy Analytics
</h1>

<p align="center">
  <strong>Monitor · Predict · Save</strong><br>
  A full-stack web application for electricity consumption analysis,<br>
  ML-powered bill forecasting, and carbon footprint tracking.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white" alt="MySQL">
  <img src="https://img.shields.io/badge/scikit--learn-1.5-F7931E?logo=scikit-learn&logoColor=white" alt="scikit-learn">
  <img src="https://img.shields.io/badge/Bootstrap-5.3-7952B3?logo=bootstrap&logoColor=white" alt="Bootstrap">
  <img src="https://img.shields.io/badge/Chart.js-4.4-FF6384?logo=chartdotjs&logoColor=white" alt="Chart.js">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

---

## Overview

Smart Energy Analytics is a **portfolio-quality, production-ready** web application that helps
households and small businesses track electricity consumption, forecast future bills using machine
learning, identify energy-wasting patterns, reduce carbon footprint, and act on personalized
cost-saving recommendations — all through a clean, dark/light-mode responsive dashboard.

Built as a final-year data-science project, the codebase demonstrates full-stack development,
data engineering, machine learning integration, and professional deployment practices.

---

## Features

| Module | Description |
|---|---|
| **Authentication** | Registration, login, logout, password reset via email, role-based access (Admin / User) |
| **Dashboard** | Real-time KPI cards — total kWh, monthly consumption, estimated bill, carbon footprint, unread alerts |
| **Analytics** | Daily / weekly / monthly / yearly breakdowns with total, average, peak, lowest, and growth rate; Chart.js line and bar charts |
| **Forecasting** | Linear Regression and Random Forest models predicting next-day, next-week, and next-month usage and bill, with MAE / RMSE / R² accuracy |
| **Appliances** | Track individual appliances (power rating + daily hours), auto-compute monthly kWh and cost, doughnut chart for consumption share |
| **Carbon Footprint** | Monthly and annual CO₂ emissions, CO₂ saved vs. baseline, trees-equivalent, and a Bronze → Platinum sustainability score |
| **Recommendations** | Rule-based + usage-driven suggestions covering appliance optimisation, peak-hour shifting, and standby-power reduction; shows monthly and annual savings |
| **Data Import** | Bulk CSV/Excel upload with validation (missing values, invalid records, duplicates, date-format errors) and a data-quality report; single-day manual entry |
| **PDF Reports** | Downloadable monthly, annual, forecast, carbon footprint, and recommendation reports generated with ReportLab |
| **Admin Panel** | Platform-wide KPIs, user management (activate/deactivate/role/delete), dataset management, alert management with pagination |
| **Dark / Light Mode** | One-click theme toggle with preference persisted in `localStorage` |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.11+ |
| **Web Framework** | Flask 3.0 (application factory pattern, blueprints) |
| **ORM / Database** | SQLAlchemy 2.0, Flask-SQLAlchemy, MySQL 8.0 |
| **Authentication** | Flask-Login, Flask-Bcrypt, itsdangerous (signed tokens) |
| **Email** | Flask-Mail (SMTP / Gmail App Password) |
| **Data Processing** | Pandas 2.2, NumPy 1.26 |
| **Machine Learning** | scikit-learn 1.5 (Linear Regression, Random Forest) |
| **PDF Generation** | ReportLab 4.2 |
| **Frontend** | Bootstrap 5.3, Chart.js 4.4, Font Awesome 6.4 |
| **Testing** | pytest, pytest-flask, coverage |
| **Deployment** | Gunicorn, Render, Railway |

---

## Folder Structure

```
smart_energy/
├── app.py                    # Application factory (create_app)
├── config.py                 # DevelopmentConfig / TestingConfig / ProductionConfig
├── requirements.txt
├── Procfile                  # gunicorn entry point
├── render.yaml               # Render deployment config
├── .env.example              # Environment variable template
├── .gitignore
│
├── database/
│   ├── schema.sql            # MySQL DDL — 8 tables with FKs, indexes, constraints
│   ├── seed_sample_data.sql  # 90 days of realistic sample data per user
│   ├── sample_usage.csv      # Demo CSV file for the data-import module
│   └── set_sample_passwords.py  # One-time script to hash seeded passwords
│
├── src/
│   ├── models/               # SQLAlchemy models
│   │   ├── user.py, electricity_usage.py, appliance.py
│   │   ├── prediction.py, alert.py, recommendation.py
│   │   ├── carbon_footprint.py, report.py
│   │
│   ├── routes/               # Flask blueprints (one per feature area)
│   │   ├── auth.py, main.py, dashboard.py, analytics.py
│   │   ├── appliances.py, forecasting.py, carbon.py
│   │   ├── recommendations.py, data_import.py, reports.py, admin.py
│   │
│   ├── services/             # Business logic layer
│   │   ├── analytics_service.py     # Daily/weekly/monthly/yearly aggregation
│   │   ├── forecasting_service.py   # Linear Regression + Random Forest
│   │   ├── carbon_service.py        # CO₂ calculation, sustainability score
│   │   ├── recommendation_service.py # Rule-based energy-saving tips
│   │   ├── report_service.py        # ReportLab PDF generation
│   │   ├── appliance_service.py     # Appliance CRUD + cost computation
│   │   ├── data_import_service.py   # CSV parsing, validation, upsert
│   │   ├── admin_service.py         # Platform KPIs, user/alert management
│   │   └── email_service.py         # Password-reset email via Flask-Mail
│   │
│   ├── templates/            # Jinja2 HTML templates
│   │   ├── base.html, partials/
│   │   ├── auth/, main/, dashboard/, analytics/
│   │   ├── appliances/, forecasting/, carbon/
│   │   ├── recommendations/, data_import/, reports/
│   │   ├── admin/, emails/
│   │
│   └── static/
│       ├── css/main.css      # Dark/light theme, CSS variables
│       └── js/main.js        # Theme toggle, password strength, chart helpers
│
├── tests/                    # pytest test suite
│   ├── conftest.py
│   ├── test_auth.py, test_password_reset.py, test_models.py
│   ├── test_dashboard.py, test_analytics.py, test_forecasting.py
│   ├── test_carbon.py, test_recommendation.py, test_reports.py
│   ├── test_data_import.py, test_admin.py, test_routes.py
│
└── uploads/                  # User-uploaded CSV files (git-ignored)
```

---

## Database Schema

Eight tables with primary keys, foreign keys with `ON DELETE CASCADE`, and composite unique constraints:

```
users                   ──┐
electricity_usage (FK)    │  ON DELETE CASCADE
appliances (FK)           │  from every child table
predictions (FK)          │
alerts (FK)               │
recommendations (FK)      │
carbon_footprint (FK)     │
reports (FK)            ──┘
```

Key constraints:
- `electricity_usage.UNIQUE(user_id, date)` — one reading per user per day
- `carbon_footprint.UNIQUE(user_id, month, year)` — one record per user per month

---

## Installation

### Prerequisites

- Python 3.11+
- MySQL 8.0+ (or MariaDB 10.5+)
- pip

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/smart-energy-analytics.git
cd smart-energy-analytics

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — set DB_PASSWORD and SECRET_KEY at minimum

# 5. Create the MySQL database
mysql -u root -p -e "CREATE DATABASE smart_energy_db CHARACTER SET utf8mb4;"

# 6. Run the schema
mysql -u root -p smart_energy_db < database/schema.sql

# 7. (Optional) Load sample data
mysql -u root -p smart_energy_db < database/seed_sample_data.sql
python database/set_sample_passwords.py

# 8. Run the app
python app.py
```

Open **http://localhost:5000**

---

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `FLASK_ENV` | Config profile (`development` / `production`) | `development` |
| `SECRET_KEY` | Session / token signing key (keep secret!) | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DB_HOST` | MySQL host | `localhost` |
| `DB_PORT` | MySQL port | `3306` |
| `DB_USER` | MySQL username | `root` |
| `DB_PASSWORD` | MySQL password | `yourpassword` |
| `DB_NAME` | Database name | `smart_energy_db` |
| `MAIL_SERVER` | SMTP server | `smtp.gmail.com` |
| `MAIL_PORT` | SMTP port | `587` |
| `MAIL_USERNAME` | Gmail address | `you@gmail.com` |
| `MAIL_PASSWORD` | Gmail App Password (16 chars) | `xxxx xxxx xxxx xxxx` |
| `MAIL_DEFAULT_SENDER` | From address | `noreply@smartenergy.com` |
| `PASSWORD_RESET_EXPIRY` | Reset link lifetime (seconds) | `3600` |
| `CO2_EMISSION_FACTOR` | kg CO₂ per kWh (India grid ≈ 0.82) | `0.82` |
| `DEFAULT_TARIFF_RATE` | ₹ per kWh | `6.50` |

> **Gmail setup:** Google Account → Security → 2-Step Verification → App Passwords.
> Generate a 16-character password for "Mail" and paste it into `MAIL_PASSWORD`.

---

## Running Locally

```bash
# Development server with auto-reload
FLASK_ENV=development python app.py

# Or using Flask CLI
flask run --debug
```

---

## Running Tests

```bash
# Full test suite
pytest tests/ -v

# With coverage report
pytest tests/ --cov=src --cov-report=term-missing

# Single file
pytest tests/test_auth.py -v
pytest tests/test_forecasting.py -v
```

The test suite uses an **in-memory SQLite database** so no MySQL setup is needed for testing.

---

## Default Login Credentials (sample data)

After loading `seed_sample_data.sql` and running `set_sample_passwords.py`:

| Role | Username | Email | Password |
|---|---|---|---|
| Admin | `admin` | `admin@smartenergy.com` | `Admin@123` |
| User | `demo_user` | `demo@smartenergy.com` | `User@123` |

---

## Deployment

### Render

1. Connect your GitHub repository to Render.
2. Set **Build Command**: `pip install -r requirements.txt`
3. Set **Start Command**: `gunicorn app:create_app() --bind 0.0.0.0:$PORT`
4. Add all environment variables from `.env.example` in Render's dashboard.
5. Provision a **MySQL** database add-on or use PlanetScale / ClearDB.

Or use the included `render.yaml` for infrastructure-as-code deployment:
```bash
# Push to your GitHub repo, then in Render dashboard:
# New → Blueprint → select your repo
```

### Railway

```bash
railway login
railway init
railway up
# Set environment variables in the Railway dashboard
```

---

## Screenshots

> Add screenshots to `docs/screenshots/` and update these paths.

| Page | Preview |
|---|---|
| Landing Page | `docs/screenshots/home.png` |
| Dashboard | `docs/screenshots/dashboard.png` |
| Analytics | `docs/screenshots/analytics.png` |
| Forecasting | `docs/screenshots/forecasting.png` |
| Carbon Dashboard | `docs/screenshots/carbon.png` |
| Admin Panel | `docs/screenshots/admin.png` |

---

## Future Improvements

- **Real-time alerts** — WebSocket push notifications when a spike is detected
- **Tariff configurator** — per-user time-of-use rates (peak / off-peak slabs)
- **Smart meter API** — direct integration with smart meter data feeds
- **Mobile app** — React Native companion app consuming the Flask API
- **OAuth login** — Google / GitHub social authentication
- **Scheduled reports** — cron-driven monthly PDF email delivery
- **Multi-household** — group accounts for property managers

---

## Authors

Developed as a **final-year B.Tech / MCA data science project** demonstrating:

- Full-stack web development with Flask and MySQL
- Machine learning integration (scikit-learn forecasting models)
- Data engineering (CSV import, cleaning, aggregation with Pandas/NumPy)
- RESTful routing and service-layer architecture
- Automated testing with pytest (12 test modules)
- Production deployment on Render / Railway

---

## License

[MIT License](LICENSE) — free to use, modify, and distribute with attribution.
