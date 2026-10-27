# 🎟️ Queueless Smart Queue — Intelligent Queue Optimization & Service Routing System

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=064E3B,047857,10B981&height=220&section=header&text=Queueless%20Smart%20Queue&fontSize=42&fontColor=ffffff&fontAlignY=38&desc=Intelligent%20Queue%20Optimization%20%26%20Service%20Routing%20System&descSize=18&descAlignY=60&descAlign=50" width="100%" alt="Queueless Header Banner" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Language-Python%203.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Framework-Flask-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask" />
  <img src="https://img.shields.io/badge/Database-SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite" />
  <img src="https://img.shields.io/badge/Deployment-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white" alt="Render" />
  <img src="https://img.shields.io/badge/Testing-Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
</p>

---

## 📌 Table of Contents

- [📖 Executive Summary](#-executive-summary)
- [🎯 Real-World Problem & Solution](#-real-world-problem--solution)
- [✨ Key Features & Capabilities](#-key-features--capabilities)
- [🏗️ System Architecture & Workflow](#️-system-architecture--workflow)
- [🔐 Role-Based Access Control (RBAC)](#-role-based-access-control-rbac)
- [🛠️ Tech Stack Matrix](#️-tech-stack-matrix)
- [⚙️ Reproducible Quickstart & Setup](#️-reproducible-quickstart--setup)
- [📁 Project Structure](#-project-structure)
- [🧪 Testing Suite](#-testing-suite)
- [👩‍💻 Author & Contributions](#-author--contributions)

---

## 📖 Executive Summary

**QueueLess** is a full-stack smart digital token orchestration and queue optimization system designed to eliminate physical waiting lines in banking halls, outpatient clinics, and government service counters. Built with **Python (Flask)**, a relational **SQLite** schema, and automated cloud continuous deployment on **Render**, the platform integrates dynamic token ticketing, algorithmic wait-time estimation, multi-counter operator dispatching, and role-based administrative analytics into a single responsive portal.

---

## 🎯 Real-World Problem & Solution

- **The Problem:** Physical queues in service counters inflict severe customer dissatisfaction, unpredictable turnaround times, counter congestion, and operational blind spots for managers unable to track service bottleneck metrics in real time.
- **The Solution:** QueueLess replaces physical line-standing with virtual token lifecycles. Customers receive instant digital tickets with estimated service times; operators call, hold, or complete tokens sequentially; and administrators monitor queue velocity and counter utilization metrics via live telemetry dashboards.

---

## ✨ Key Features & Capabilities

- **🎫 Dynamic Token Dispensing:** Instant token creation with categorical service prioritization (e.g., General, Priority, Senior).
- **⏱️ Algorithmic Wait Estimation:** Rolling average turnaround calculation factoring in queue depth and counter throughput.
- **🔐 Multi-Tier RBAC Architecture:** Granular access isolation across **Admin**, **Operator / Teller**, and **Customer** personas.
- **🖥️ Operator Service Station:** Single-click token dispatch (`Call Next`, `Mark In-Progress`, `Resolve`, `No-Show`).
- **📊 Real-Time Operations Telemetry:** Executive counters displaying Total Issued, Active Serving, Completed, and Average Wait Time.
- **☁️ Cloud Continuous Deployment:** Pre-configured `render.yaml` and `Procfile` ready for zero-downtime production deployment.

---

## 🏗️ System Architecture & Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      QueueLess Architecture Overview                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
     ┌─────────────────────────────────┼────────────────────────────────┐
     ▼                                 ▼                                ▼
┌──────────────┐              ┌────────────────┐              ┌──────────────────┐
│   Customer   │              │ Counter Teller │              │    System Admin  │
│  (Get Token) │              │ (Call & Serve) │              │  (Monitor & SLA) │
└──────┬───────┘              └───────┬────────┘              └────────┬─────────┘
       │                              │                                │
       └──────────────────────────────┼────────────────────────────────┘
                                      ▼
                        ┌───────────────────────────┐
                        │    Flask Application Core │
                        │  (Routing, Auth, State)   │
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │ SQLite Relational Schema  │
                        │ (Users, Tokens, Counters) │
                        └───────────────────────────┘
```

---

## 🔐 Role-Based Access Control (RBAC)

| Role | Permissions & Accessible Views |
| :--- | :--- |
| **Customer** | Generate new queue token, view current ticket status, track dynamic estimated wait time. |
| **Operator / Teller** | Access designated counter console, advance queue, resolve or transfer tokens. |
| **Administrator** | Manage counters, provision staff credentials, inspect SLA metrics, reset daily queues. |

---

## 🛠️ Tech Stack Matrix

| Layer | Technology | Details |
| :--- | :--- | :--- |
| **Backend** | Python 3.10+, Flask | Modular application factory, session auth, REST endpoints |
| **Database** | SQLite, SQLAlchemy / DB API | Relational schema with foreign keys and timestamped logs |
| **Frontend** | Jinja2, HTML5, CSS3, JavaScript | Responsive mobile-ready UI with dynamic polling updates |
| **Testing** | Pytest | Unit and integration tests covering token state machines |
| **Deployment** | Render, Gunicorn, Procfile | Automated cloud hosting with environment variable injection |

---

## ⚙️ Reproducible Quickstart & Setup

### Prerequisites
- Python 3.10+ and Git installed on your system.

### 1. Clone the Repository
```bash
git clone https://github.com/keerthi19hub/queueless-smart-queue.git
cd queueless-smart-queue
```

### 2. Setup Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Initialize Database & Run
```bash
# Run application (auto-initializes SQLite database)
python run.py
# Or: flask run
```
Open your browser and navigate to `http://localhost:5000`.

---

## 📁 Project Structure

```text
queueless-smart-queue/
├── app.py              # Application initialization and route controllers
├── run.py              # Execution entry point
├── config.py           # Environment and database configuration
├── auth.py             # User authentication and password hashing routines
├── db.py               # SQLite connection management and helpers
├── models.py           # Relational data entities (Token, User, Counter)
├── services/           # Queue scheduling and wait estimation algorithms
├── templates/          # Jinja2 templates (Customer, Operator, Admin dashboards)
├── static/             # Custom CSS styling, client-side JS, and assets
├── tests/              # Pytest automated test suites
├── render.yaml         # Render cloud infrastructure blueprint
├── Procfile            # Production WSGI process declaration
├── requirements.txt    # Application dependencies
└── README.md           # Project documentation
```

---

## 🧪 Testing Suite

Execute automated integration tests verifying token generation, authentication, and state transitions:
```bash
pytest tests/ -v
```

---

## 👩‍💻 Author & Contributions

**Keerthi N**  
- **GitHub:** [@keerthi19hub](https://github.com/keerthi19hub)  
- **Portfolio:** [keerthi19hub.github.io](https://keerthi19hub.github.io)  
- **Role:** Full backend architecture, database schema design, token state machine implementation, automated tests, and cloud deployment.

---

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=064E3B,047857,10B981&height=100&section=footer" width="100%" alt="Footer Banner" />
</p>
