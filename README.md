# 🦺 PPE Compliance Monitoring System

> AI-powered real-time Personal Protective Equipment detection and safety compliance monitoring for industrial environments.

Built during internship at **Tata Technologies** (AI/ML Division) — fully functional on CPU-only hardware with no GPU required.

---

## 📌 Overview

The PPE Compliance Monitoring System is a full-stack computer vision application that automatically detects PPE violations from live CCTV or IP camera footage. It identifies missing safety equipment in real time, logs every violation with a timestamped annotated snapshot, and displays everything on a live web dashboard.

The system replaces manual safety monitoring — which is limited by human fatigue, coverage gaps, and lack of audit trails — with continuous, automated, objective enforcement.

---

## ✨ Features

- 🎯 **Real-time detection** of 5 PPE items — Hard Hat, Safety Vest, Gloves, Face Mask, Safety Boots — using YOLOv8n at 10 fps on CPU
- 🚨 **Smart violation engine** with 5-frame consecutive filter and 30-second per-camera cooldown to eliminate false alerts
- 📸 **Auto snapshot capture** — annotated JPEG saved to disk for every confirmed violation
- 🗄️ **PostgreSQL logging** — every violation stored with UUID, camera ID, missing PPE list, confidence score, timestamp, and resolved status
- 📡 **WebSocket live streaming** — annotated frames delivered to the browser as Base64 JPEG in real time
- 🖥️ **React dashboard** — live feed, per-PPE status checklist, violation log with thumbnails, analytics charts, compliance score
- 📊 **Chart.js analytics** — 7-day trend (bar + line), per-PPE breakdown, per-camera doughnut, compliance score ring
- 🔍 **Filters** — filter violation log by camera and PPE type
- ✅ **Mark resolved** — supervisor can mark incidents as resolved with notes
- 📁 **CSV export** — download full violation history as a spreadsheet
- 📹 **Dual source support** — toggle between pre-recorded MP4 file and live RTSP/webcam stream with one config line
- 🔁 **Auto-reconnect** — WebSocket and RTSP connections recover automatically on drop
- 🔌 **13 REST endpoints** — full API with interactive docs at `/docs`

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| AI Detection | YOLOv8n (Ultralytics) |
| Computer Vision | OpenCV 4.x |
| Backend | FastAPI + Uvicorn (ASGI) |
| Streaming | WebSocket — Base64 JPEG |
| Database ORM | SQLAlchemy + psycopg2 |
| Database | PostgreSQL 15 |
| Frontend | React 18 + Tailwind CSS |
| Charts | Chart.js + react-chartjs-2 |
| HTTP Client | Axios |
| Config | python-dotenv |

---

## 📁 Project Structure

```text
ppe-monitor/
├── backend/
│   ├── init.py
│   ├── main.py              ← FastAPI app, WebSocket stream, REST endpoints
│   ├── violation_engine.py  ← Frame filter, cooldown, snapshot capture
│   ├── database.py          ← SQLAlchemy models, PostgreSQL connection
│   └── db_writer.py         ← Save/read violation records
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── index.js
│       ├── index.css
│       └── components/
│           ├── LiveFeed.jsx        ← WebSocket video + PPE checklist
│           ├── ViolationLog.jsx    ← Incident list + filters + CSV export
│           ├── StatsBar.jsx        ← Live counters + flash animation
│           ├── AnalyticsPanel.jsx  ← Chart.js charts + compliance score
│           └── CameraSelector.jsx  ← Multi-camera selector sidebar
├── violations/              ← Auto-saved JPEG snapshots (git-ignored)
├── detector_test.py         ← Standalone detection test (Phase 2)
├── test_phase3.py           ← Violation engine + DB verification script
├── verify_setup.py          ← Phase 1 environment check script
├── requirements.txt
├── .env.example
└── README.md

**Note:** `best.pt` (model weights), `test_video.mp4`, and `.env` are not included in this repository. See setup instructions below.

---

## 🚀 Setup & Installation

### Prerequisites

- Python 3.9+
- PostgreSQL 15
- Node.js 18+
- A trained YOLOv8n model file (`best.pt`) — see [Model section](#-model) below

---

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/ppe-compliance-monitor.git
cd ppe-compliance-monitor
```

---

### 2. Python environment

```bash
# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

### 3. PostgreSQL database

Create a database called `ppe_monitor` in PostgreSQL. Using pgAdmin or psql:

```sql
CREATE DATABASE ppe_monitor;
```

Tables are created automatically on first run via SQLAlchemy's `init_db()`.

---

### 4. Environment variables

Create a `.env` file in the project root:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ppe_monitor
DB_USER=postgres
DB_PASSWORD=your_postgres_password
```

---

### 5. Add required files

Place these in the project root (not included in repo):
ppe-monitor/
├── best.pt          ← your trained YOLOv8n model
└── test_video.mp4   ← demo video (optional, for file mode)

---

### 6. Verify setup

```bash
python verify_setup.py
```

All 11 checks should show ✓ including model class names, PostgreSQL connection, and all Python packages.

---

### 7. Run the backend

```bash
uvicorn backend.main:app --port 8000 --workers 1
```

Visit `http://127.0.0.1:8000` to confirm the API is running.
Visit `http://127.0.0.1:8000/docs` for interactive API documentation.

---

### 8. Run the frontend

```bash
cd frontend
npm install
npm install axios
npm install -D tailwindcss@3 postcss autoprefixer
npm start
```

Open `http://localhost:3000` in your browser.

---

## ⚙️ Configuration

All key settings are at the top of `backend/main.py`:

```python
# Switch between pre-recorded file and live camera
SOURCE_MODE = "file"       # "file" or "rtsp"

VIDEO_FILE  = "test_video.mp4"

RTSP_SOURCES = {
    "CAM_01": "0",                              # laptop webcam
    "CAM_02": "http://192.168.x.x:8080/video", # phone via IP Webcam app
    "CAM_03": "test_video.mp4",                 # pre-recorded fallback
}

REQUIRED_PPE    = ['Hard_hat', 'Vest', 'Gloves', 'Mask', 'Safety_boots']
CONFIDENCE      = 0.60   # detection confidence threshold
PROCESS_EVERY_N = 3      # process every Nth frame (CPU performance)
TARGET_FPS      = 10     # target WebSocket frame rate
```

---
