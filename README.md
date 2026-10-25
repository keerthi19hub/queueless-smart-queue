# QueueLess — Smart Queue Management System

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/keerthi19hub/queueless-smart-queue)

**QueueLess** is a modern, responsive, and full-featured web-based queue management system engineered for college campuses, examination centers, administrative offices, and public service institutions. It replaces physical waiting lines with instant digital tokens, real-time queue position tracking, estimated wait time countdowns, sound and desktop notifications, and a multi-counter staff administration dashboard.

---

## 🌟 Key Features

### 1. Visitor Interface
- **Digital Token Generation**: Select campus departments (Administration, Fee Payment, Student Support, General Desk) and generate a sequential token (e.g. `ADM-101`, `FEE-101`).
- **Duplicate Prevention**: Client-side debouncing and server-side idempotency keys guarantee that refreshing or repeated clicks never generate duplicate tokens.
- **Privacy First**: Secure reference codes (e.g. `QL-9X4K2M`) ensure visitors access only their own ticket and status without exposing other visitors' personal records.
- **Live Status Tracking (`/status/<ref_code>`)**: Smart lightweight polling every 3 seconds updates the visitor on:
  - Exact number of people ahead in line
  - Current token being served at the counter
  - Estimated wait time calculated dynamically based on configurable department duration
  - Visual 5-step progress stepper: `Token Issued` &rarr; `Waiting` &rarr; `Turn Approaching` &rarr; `Now Serving` &rarr; `Completed`
- **Multi-Channel Notification System**:
  - In-website toast alerts
  - Browser Desktop Notifications (`Notification API`) with permission prompt
  - Web Audio API synthetic audio chime when turn is approaching and when called
  - Mobile device vibration (`navigator.vibrate`) when called

### 2. Staff Administrator Dashboard (`/admin`)
- **Secure Authentication**: Salted and hashed passwords with Scrypt via `werkzeug.security`.
- **Live Overview Metrics**: Total tokens issued today, waiting count, active serving count, completed count, and average service time per visitor.
- **Multi-Counter Operations**:
  - **Call Next Token**: Automatically advances queue, completes previous visitor, and alerts the next visitor.
  - **Complete Token**: Marks the current visitor as served and logs duration.
  - **Skip / Absent**: Flags unresponsive visitors.
  - **Re-announce / Recall**: Re-triggers sound chime and alert for visitors who didn't hear their call.
  - **Queue Reset**: Safely clears or archives pending queues.
- **Token Registry & Audit Trail**: Searchable, filterable list of all tokens by status (`ALL`, `WAITING`, `SERVING`, `COMPLETED`, `SKIPPED`).
- **Configuration & Settings (`/admin/settings`)**: Secure password change form and live department counter duration editor.

### 3. Public TV / Kiosk Display Board (`/display`)
- High-contrast, full-screen waiting hall board optimized for TVs and monitors.
- Displays all department counters, current serving token in large typography, upcoming tokens, live clock, and audio announcements on new calls.

---

## 🛠️ Technology Stack

| Layer | Technology | Details |
|---|---|---|
| **Backend** | Python 3.11+ / Flask 3.1 | Clean, lightweight WSGI architecture |
| **Database** | SQLite with WAL mode / PostgreSQL | Persistent file storage with WAL (Write-Ahead Logging) or Cloud PostgreSQL |
| **ORM** | SQLAlchemy 2.0 | Scoped thread-safe sessions and connection pooling |
| **Frontend** | HTML5, CSS3, Vanilla Modern JavaScript | No bloated frameworks; fast, zero-delay load times |
| **Audio** | HTML5 Web Audio API | Synthetic synthesized bell chimes (zero missing audio assets) |
| **Deployment** | Render / Railway / PythonAnywhere | Configured with `render.yaml` Blueprint & persistent 1GB disk |

---

## 🚀 1-Click Public Cloud Deployment

The repository is hosted on GitHub:
**`https://github.com/keerthi19hub/queueless-smart-queue`**

### Option A: 1-Click Deployment on Render.com (Recommended for College Submission)
1. Visit the Render 1-click deployment link:
   👉 **[Deploy QueueLess on Render](https://render.com/deploy?repo=https://github.com/keerthi19hub/queueless-smart-queue)**
2. Sign in with your GitHub account (`keerthi19hub`).
3. Render automatically detects `render.yaml`, configures a persistent 1GB storage disk for the SQLite database, and deploys the application.
4. Once deployed, Render gives you your permanent public HTTPS URL (e.g. `https://queueless-xxxx.onrender.com`).
5. Submit this URL in your college project submission form!

### Option B: Deploying on Railway
1. Go to [Railway.app](https://railway.app/) and sign in with GitHub.
2. Click **New Project** &rarr; **Deploy from GitHub repo** &rarr; Select `queueless-smart-queue`.
3. Railway automatically builds and deploys the app using `Procfile`.
4. Generate a public domain under **Settings** &rarr; **Networking**.

---

## 💻 Running Locally

### 1. Clone the repository
```bash
git clone https://github.com/keerthi19hub/queueless-smart-queue.git
cd queueless-smart-queue
```

### 2. Create and activate a virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Start the application
```bash
python run.py
```
Open your browser and navigate to:
- **Visitor Portal**: `http://127.0.0.1:5000`
- **Staff Admin Dashboard**: `http://127.0.0.1:5000/admin`
- **Public TV Display**: `http://127.0.0.1:5000/display`

---

## 🔐 Administrator Credentials

| Parameter | Value |
|---|---|
| **Login URL** | `/admin/login` |
| **Default Username** | `admin` |
| **Default Password** | `QueueLessAdmin2026!` |

> **Security Note:** You can change this password at any time via the **Admin Settings** page (`/admin/settings`).

---

## 🧪 Automated Testing

QueueLess comes with an automated test suite covering all visitor workflows, concurrency idempotency, administrator operations, and edge cases.

To execute tests:
```bash
python -m unittest tests/test_app.py
```

### Verified Test Cases:
- [x] Database auto-seeding of default campus services and admin user
- [x] Service catalog retrieval
- [x] Sequential token number generation (`ADM-101`, `ADM-102`...)
- [x] Duplicate prevention via client idempotency keys
- [x] Live position and estimated wait time calculation
- [x] Secure password authentication and authorization checks
- [x] Administrator counter advancement (`call-next`, `complete`, `skip`, `recall`)
- [x] Visitor voluntary token cancellation
- [x] Graceful empty queue handling
- [x] Health check (`/health`) and public kiosk data endpoints

---

## 📡 API Reference Catalog

| Endpoint | Method | Description |
|---|---|---|
| `/health` | `GET` | Health check and database status |
| `/api/services` | `GET` | List active services, current serving, and waiting counts |
| `/api/token/generate` | `POST` | Generate new token (with idempotency check) |
| `/api/token/status/<ref_code>` | `GET` | Fetch live status, people ahead, estimated wait time, and events |
| `/api/token/cancel` | `POST` | Visitor self-service queue cancellation |
| `/api/display` | `GET` | Public TV kiosk display board data |
| `/api/admin/call-next` | `POST` | Admin: Advance queue and call next visitor |
| `/api/admin/complete` | `POST` | Admin: Mark current visitor as served |
| `/api/admin/skip` | `POST` | Admin: Mark visitor as skipped |
| `/api/admin/recall` | `POST` | Admin: Re-announce current visitor |
| `/api/admin/reset` | `POST` | Admin: Reset or clear active queue |
| `/api/admin/change-password` | `POST` | Admin: Secure password change |
| `/api/admin/service/update` | `POST` | Admin: Update counter name, average service time, or status |

---

## 🎓 College Project Viva & Evaluation Notes

1. **Why SQLite with WAL mode instead of in-memory or heavy relational servers?**
   SQLite with Write-Ahead Logging (`PRAGMA journal_mode=WAL`) allows concurrent reads while writes are occurring without database locking. It provides high-performance persistent storage with zero external database server costs, ideal for departmental queue management.
2. **How is real-time synchronization handled?**
   Using lightweight HTTP polling with small, optimized JSON payloads (less than 1KB) every 3 seconds. This avoids WebSocket handshake overhead and firewall restrictions on institutional networks while ensuring instant UI synchronization.
3. **How are duplicate tokens prevented?**
   Every token form generates a UUID idempotency key on load. If a user double-clicks or refreshes, the backend detects the duplicate key and returns the existing token rather than creating a new sequence.
