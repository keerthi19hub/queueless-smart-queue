# 🎟️ QueueLess — Smart Queue & Token Management System

> **Full-stack digital queue management web application with automated ticketing, real-time wait estimation, and role-based administration.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)](https://sqlite.org)
[![Render](https://img.shields.io/badge/Deployed_on-Render-46E3B7?logo=render&logoColor=white)](https://render.com)

---

## Problem Statement

Physical queues in service counters and institutions cause customer friction, unpredictable wait times, and administrative bottlenecks. QueueLess digitises this process entirely.

## Key Features

- **🎟️ Automated Token Generation:** Unique tokens issued per customer with real-time queue position.
- **⏱️ Wait Time Estimation:** Dynamic calculation based on average service rate and queue depth.
- **🔐 Role-Based Access Control (RBAC):** Separate dashboards and permissions for Admins, Operators, and Customers.
- **📊 Queue Monitoring:** Live dashboard showing active tokens, completed service, and pending counts.
- **🧪 Automated Tests:** `pytest` test suite covering token lifecycle, auth, and queue logic.
- **☁️ Cloud Deployment:** Deployed and hosted on **Render**.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python · Flask |
| Database | SQLite (relational schema) |
| Frontend | Jinja2 · Bootstrap · HTML5/CSS3 |
| Auth | Flask-Login · Session management |
| Testing | pytest |
| Deployment | Render |

## Quickstart

```bash
# 1. Clone
git clone https://github.com/keerthi19hub/queueless-smart-queue.git
cd queueless-smart-queue

# 2. Setup virtual environment
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initialise database
python init_db.py

# 5. Run application
python app.py
# Open http://localhost:5000

# 6. Run tests
pytest tests/
```

## Architecture

```
queueless-smart-queue/
├── app.py              # Flask application factory & routes
├── models.py           # SQLAlchemy/SQLite schema: Token, User, Queue
├── auth/               # Login, registration, session management
├── admin/              # Admin panel routes & dashboard logic
├── templates/          # Jinja2 HTML templates
├── static/             # CSS, JS, Bootstrap assets
├── tests/              # pytest test suite
├── init_db.py          # Database initialisation script
└── requirements.txt
```

## Author

**Keerthi N** — Complete backend development, relational database schema, token lifecycle state machine, session authentication, and automated test suite.

*Alliance University, BCA — 2026*

---

Released under the [MIT License](https://opensource.org/licenses/MIT).
