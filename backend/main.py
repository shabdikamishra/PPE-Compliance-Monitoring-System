import os
os.environ["CUDA_VISIBLE_DEVICES"]  = ""
os.environ["OPENBLAS_NUM_THREADS"]  = "1"
os.environ["OMP_NUM_THREADS"]       = "1"
os.environ["MKL_NUM_THREADS"]       = "1"
os.environ["NUMEXPR_NUM_THREADS"]   = "1"
os.environ["TORCH_NUM_THREADS"]     = "2"

import cv2
import asyncio
import base64
import json
import time
import os
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from .database import init_db, SessionLocal, Violation
from .violation_engine import ViolationEngine
from .db_writer import save_violation, get_recent_violations, get_stats

load_dotenv()

# Default model path (can be overridden via .env)
MODEL_PATH = os.getenv("MODEL_PATH", "best.pt")

# Default camera id for status endpoints
CAMERA_ID = os.getenv("CAMERA_ID", "CAM_01")

# ─────────────────────────────────────────────
#  SOURCE CONFIGURATION
#  Switch SOURCE_MODE between 'file' and 'rtsp'
# ─────────────────────────────────────────────
PROCESS_EVERY_N_FILE = 3
PROCESS_EVERY_N_RTSP = 5     # skip more frames for live cameras


SOURCE_MODE = "rtsp"          # ← change to "rtsp" for live camera

# File mode — pre-recorded video
VIDEO_FILE  = "test_video.mp4"

# RTSP mode — live camera sources per camera ID
# Replace these URLs with your actual camera IPs
RTSP_SOURCES = {
    "CAM_01": "http://10.44.168.198:8080/video",   # phone via IP Webcam app
    "CAM_02": "0",                                # same phone, second feed
    "CAM_03": "test_video.mp4",                   # fallback to file for cam 3
}

def get_video_source(camera_id: str) -> str:
    """Return the correct video source for a given camera ID."""
    if SOURCE_MODE == "rtsp":
        source = RTSP_SOURCES.get(camera_id, VIDEO_FILE)
        print(f"[Source] {camera_id} → RTSP: {source}")
        return source
    else:
        print(f"[Source] {camera_id} → File: {VIDEO_FILE}")
        return VIDEO_FILE

# Your model's PPE classes (present = wearing it)
REQUIRED_PPE    = ['Hard_hat', 'Vest', 'Gloves', 'Mask', 'Safety_boots']

# All classes and their display colors (for frontend reference)
CLASS_COLORS = {
    'Hard_hat'     : '#00C800',
    'Vest'         : '#00C800',
    'Gloves'       : '#00C800',
    'Mask'         : '#00C800',
    'Safety_boots' : '#00C800',
    'Person'       : '#FFA500',
}

CONFIDENCE      = 0.60
PROCESS_EVERY_N = 3
TARGET_FPS      = 10       # frames sent to frontend per second
SNAPSHOT_DIR    = "violations"

# ─────────────────────────────────────────────
#  APP SETUP
# ─────────────────────────────────────────────

app = FastAPI(title="PPE Compliance Monitor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],   # React dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve violation snapshots as static files
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
app.mount("/snapshots", StaticFiles(directory=SNAPSHOT_DIR), name="snapshots")

_model  = None
_engine = None

def get_model():
    global _model
    if _model is None:
        print("[Model] Loading YOLOv8...")
        _model = YOLO(MODEL_PATH)
        _model.to('cpu')
        print(f"[Model] Loaded ✓  Classes: {_model.names}")
    return _model

def get_engine():
    global _engine
    if _engine is None:
        _engine = ViolationEngine(
            cooldown_seconds = 30,
            min_frames       = 5,
            snapshot_dir     = SNAPSHOT_DIR,
            required_ppe     = REQUIRED_PPE
        )
        print("[Engine] Initialized ✓")
    return _engine

# ─────────────────────────────────────────────
#  LOAD MODEL + ENGINE ON STARTUP
# ─────────────────────────────────────────────

from ultralytics import YOLO

print("[Startup] Initializing database...")
init_db()

print("[Startup] Loading YOLOv8 model...")
model = YOLO(MODEL_PATH)
print(f"[Startup] Model loaded. Classes: {model.names}")

print("[Startup] Creating violation engine...")
violation_engine = ViolationEngine(
    cooldown_seconds = 30,
    min_frames       = 5,
    snapshot_dir     = SNAPSHOT_DIR,
    required_ppe     = REQUIRED_PPE
)

print("[Startup] Ready ✓")

# ─────────────────────────────────────────────
#  CONNECTION MANAGER (tracks active WebSockets)
# ─────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active = {}

    async def connect(self, camera_id, ws):
        await ws.accept()
        if camera_id not in self.active:
            self.active[camera_id] = []

        # Close stale connections if too many accumulate
        if len(self.active[camera_id]) > 3:
            print(f"[WS] Too many connections for {camera_id} — clearing stale ones")
            for old_ws in self.active[camera_id][:-1]:
                try:
                    await old_ws.close()
                except Exception:
                    pass
            self.active[camera_id] = []

        self.active[camera_id].append(ws)
        print(f"[WS] Connected → {camera_id} "
              f"(total: {len(self.active[camera_id])})")

    def disconnect(self, camera_id, ws):
        if camera_id in self.active:
            try:
                self.active[camera_id].remove(ws)
            except ValueError:
                pass
        print(f"[WS] Disconnected → {camera_id}")

    async def send(self, camera_id, ws, data):
        try:
            await ws.send_text(data)
        except Exception:
            self.disconnect(camera_id, ws)

manager = ConnectionManager()

# ─────────────────────────────────────────────
#  HELPER — draw custom boxes on frame
# ─────────────────────────────────────────────

import numpy as np

def draw_boxes(frame, results, model_names):
    """Draw custom bounding boxes — green for PPE, orange for Person."""
    COLOR_MAP = {
        'Hard_hat'     : (0, 200,   0),
        'Vest'         : (0, 200,   0),
        'Gloves'       : (0, 200,   0),
        'Mask'         : (0, 200,   0),
        'Safety_boots' : (0, 200,   0),
        'Person'       : (255, 165,  0),
    }
    DEFAULT_COLOR = (200, 200, 200)

    for box in results.boxes:
        cls_id   = int(box.cls)
        cls_name = model_names[cls_id]
        conf     = float(box.conf)
        x1, y1, x2, y2 = map(int, box.xyxy[0])

        color = COLOR_MAP.get(cls_name, DEFAULT_COLOR)

        # Box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # Corner accents
        L = 12
        T = 3
        cv2.line(frame, (x1, y1), (x1+L, y1), color, T)
        cv2.line(frame, (x1, y1), (x1, y1+L), color, T)
        cv2.line(frame, (x2, y1), (x2-L, y1), color, T)
        cv2.line(frame, (x2, y1), (x2, y1+L), color, T)
        cv2.line(frame, (x1, y2), (x1+L, y2), color, T)
        cv2.line(frame, (x1, y2), (x1, y2-L), color, T)
        cv2.line(frame, (x2, y2), (x2-L, y2), color, T)
        cv2.line(frame, (x2, y2), (x2, y2-L), color, T)

        # Label
        label = f"{cls_name} {conf:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (x1, y1-th-8), (x1+tw+8, y1), color, -1)
        cv2.putText(frame, label, (x1+4, y1-4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1, cv2.LINE_AA)

    return frame


def draw_banner(frame, is_violation, missing_ppe, frame_w):
    """Draw top status banner."""
    banner_h = 52
    if is_violation:
        pulse = int(abs(np.sin(time.time() * 3)) * 35)
        color = (0, 0, 180 + pulse)
        text  = f"!  VIOLATION — Missing: {', '.join(missing_ppe)}"
    else:
        color = (34, 139, 34)
        text  = "✓  ALL PPE COMPLIANT"

    cv2.rectangle(frame, (0, 0), (frame_w, banner_h), color, -1)
    cv2.line(frame, (0, banner_h), (frame_w, banner_h), (255,255,255), 1)
    cv2.putText(frame, text, (16, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255,255,255), 2, cv2.LINE_AA)

    ts = datetime.now().strftime("%H:%M:%S")
    cv2.putText(frame, ts, (frame_w - 90, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 1, cv2.LINE_AA)
    return frame

# ─────────────────────────────────────────────
#  REST ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "status"  : "PPE Monitor API is running",
        "version" : "1.0.0",
        "endpoints": [
            "/api/violations",
            "/api/stats",
            "/api/cameras",
            "/ws/stream/{camera_id}"
        ]
    }


@app.get("/api/stats")
def api_stats():
    stats = get_stats()
    engine_status = violation_engine.get_status(CAMERA_ID)
    return {
        "total"            : stats["total"],
        "today"            : stats["today"],
        "cameras_active"   : 1,
        "required_ppe"     : REQUIRED_PPE,
        "cooldown_seconds" : violation_engine.cooldown_seconds,
        "min_frames"       : violation_engine.min_frames,
    }


@app.get("/api/violations")
def api_violations(limit: int = 50):
    rows = get_recent_violations(limit=limit)
    return [
        {
            "id"          : str(r.id),
            "camera_id"   : r.camera_id,
            "missing_ppe" : r.missing_ppe,
            "detected_ppe": r.detected_ppe,
            "confidence"  : r.confidence,
            "timestamp"   : r.timestamp.isoformat(),
            "image_url"   : (
                f"http://localhost:8000/snapshots/"
                f"{os.path.basename(r.image_path)}"
                if r.image_path else None
            ),
        }
        for r in rows
    ]


@app.get("/api/violations/{violation_id}")
def api_violation_detail(violation_id: str):
    db = SessionLocal()
    try:
        import uuid
        row = db.query(Violation).filter(
            Violation.id == uuid.UUID(violation_id)
        ).first()
        if not row:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")
        return {
            "id"          : str(row.id),
            "camera_id"   : row.camera_id,
            "missing_ppe" : row.missing_ppe,
            "detected_ppe": row.detected_ppe,
            "confidence"  : row.confidence,
            "timestamp"   : row.timestamp.isoformat(),
            "image_url"   : (
                f"http://localhost:8000/snapshots/"
                f"{os.path.basename(row.image_path)}"
                if row.image_path else None
            ),
        }
    finally:
        db.close()


@app.get("/api/cameras")
def api_cameras():
    return [
        {"id": "CAM_01", "name": "Main Entrance",    "zone": "Gate A",    "active": True},
        {"id": "CAM_02", "name": "Production Floor",  "zone": "Zone B",    "active": True},
        {"id": "CAM_03", "name": "Loading Bay",       "zone": "Zone C",    "active": True},
    ]

# ─────────────────────────────────────────────
#  WEBSOCKET — live video stream per camera
# ─────────────────────────────────────────────

@app.websocket("/ws/stream/{camera_id}")
async def stream(websocket: WebSocket, camera_id: str):
    await manager.connect(camera_id, websocket)

    model  = get_model()
    engine = get_engine()

    frame_count     = 0
    sleep_time      = 1.0 / TARGET_FPS
    cap             = None
    reconnect_delay = 2

    process_every_n = PROCESS_EVERY_N_RTSP if SOURCE_MODE == "rtsp" else PROCESS_EVERY_N_FILE
    target_size     = (416, 234) if SOURCE_MODE == "rtsp" else (640, 360)

    def open_capture(cam_id):
        source = get_video_source(cam_id)
        if isinstance(source, str) and source.isdigit():
            source = int(source)

        c = cv2.VideoCapture(source)
        if SOURCE_MODE == "rtsp":
            c.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            c.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
            c.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)

        if not c.isOpened():
            print(f"[WS] Could not open source for {cam_id}")
            return None

        print(f"[WS] Stream opened for {cam_id}")
        return c

    try:
        cap = open_capture(camera_id)

        while True:
            if cap is None or not cap.isOpened():
                print(f"[WS] Reconnecting {camera_id} in {reconnect_delay}s...")
                await asyncio.sleep(reconnect_delay)
                if cap:
                    cap.release()
                cap = open_capture(camera_id)
                continue

            ret, frame = cap.read()

            if not ret:
                if SOURCE_MODE == "file":
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    await asyncio.sleep(0.05)
                    continue
                else:
                    print(f"[WS] Frame read failed for {camera_id} — reconnecting...")
                    cap.release()
                    cap = None
                    await asyncio.sleep(reconnect_delay)
                    continue

            # Drop stale buffered frames for live streams
            if SOURCE_MODE == "rtsp":
                for _ in range(3):
                    cap.grab()
                ret2, latest = cap.retrieve()
                if ret2:
                    frame = latest

            frame_count += 1

            if frame_count % process_every_n != 0:
                await asyncio.sleep(0.01)
                continue

            frame = cv2.resize(frame, target_size)
            h, w  = frame.shape[:2]

            # ── Run inference WITHOUT blocking the event loop ──
            results = await asyncio.to_thread(model, frame, conf=CONFIDENCE, verbose=False)
            results = results[0]

            detected_classes = [model.names[int(b.cls)] for b in results.boxes]

            avg_conf = (
                float(sum(float(b.conf) for b in results.boxes) / len(results.boxes))
                if results.boxes else 0.0
            )

            annotated    = frame.copy()
            draw_boxes(annotated, results, model.names)

            missing_ppe  = [p for p in REQUIRED_PPE if p not in detected_classes]
            is_violation = len(missing_ppe) > 0
            draw_banner(annotated, is_violation, missing_ppe, w)

            event = engine.process(
                camera_id        = camera_id,
                detected_classes = detected_classes,
                frame            = annotated,
                avg_confidence   = avg_conf
            )

            if event:
                save_violation(event)

            _, buf    = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 60])
            frame_b64 = base64.b64encode(buf).decode('utf-8')

            payload = {
                "frame"          : frame_b64,
                "camera_id"      : camera_id,
                "is_violation"   : is_violation,
                "missing_ppe"    : missing_ppe,
                "detected"       : detected_classes,
                "violation_fired": event is not None,
                "timestamp"      : datetime.now().isoformat(),
                "source_mode"    : SOURCE_MODE,
                "stats"          : get_stats(),
            }

            await manager.send(camera_id, websocket, json.dumps(payload))
            await asyncio.sleep(sleep_time)

    except WebSocketDisconnect:
        manager.disconnect(camera_id, websocket)
    except Exception as e:
        print(f"[WS] Stream error ({camera_id}): {e}")
        manager.disconnect(camera_id, websocket)
    finally:
        if cap:
            cap.release()
        print(f"[WS] Stream closed → {camera_id}")


@app.get("/api/compliance-score")
def api_compliance_score():
    from datetime import datetime, timedelta
    db = SessionLocal()
    try:
        # Today's violations
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_violations = db.query(Violation).filter(
            Violation.timestamp >= today_start
        ).count()

        # Score: assume 100 detection cycles per hour, 9 working hours
        
        TOTAL_CYCLES = 900
        violations_capped = min(today_violations, TOTAL_CYCLES)
        score = round(((TOTAL_CYCLES - violations_capped) / TOTAL_CYCLES) * 100, 1)

        # Per-PPE breakdown from recent violations
        recent = db.query(Violation).filter(
            Violation.timestamp >= today_start
        ).all()

        ppe_counts = {}
        for v in recent:
            for item in (v.missing_ppe or []):
                ppe_counts[item] = ppe_counts.get(item, 0) + 1

        return {
            "score"          : score,
            "today_violations": today_violations,
            "total_cycles"   : TOTAL_CYCLES,
            "ppe_breakdown"  : ppe_counts,
            "rating"         : "Excellent" if score >= 90 else
                               "Good"      if score >= 75 else
                               "Fair"      if score >= 60 else "Poor"
        }
    finally:
        db.close()

from sqlalchemy import func

@app.get("/api/violations/filtered")
def api_violations_filtered(
    camera_id : str = None,
    ppe_type  : str = None,
    date_from : str = None,
    date_to   : str = None,
    limit     : int = 100
):
    from datetime import datetime
    db = SessionLocal()
    try:
        q = db.query(Violation)

        if camera_id:
            q = q.filter(Violation.camera_id == camera_id)
        if date_from:
            q = q.filter(Violation.timestamp >= datetime.fromisoformat(date_from))
        if date_to:
            q = q.filter(Violation.timestamp <= datetime.fromisoformat(date_to))
        if ppe_type:
            q = q.filter(Violation.missing_ppe.contains([ppe_type]))

        rows = q.order_by(Violation.timestamp.desc()).limit(limit).all()
        return [
            {
                "id"         : str(r.id),
                "camera_id"  : r.camera_id,
                "missing_ppe": r.missing_ppe,
                "detected_ppe":r.detected_ppe,
                "confidence" : r.confidence,
                "timestamp"  : r.timestamp.isoformat(),
                "image_url"  : (
                    f"http://localhost:8000/snapshots/{os.path.basename(r.image_path)}"
                    if r.image_path else None
                ),
                "resolved"   : getattr(r, 'resolved', False),
            }
            for r in rows
        ]
    finally:
        db.close()


@app.get("/api/trends")
def api_trends():
    from datetime import datetime, timedelta
    db = SessionLocal()
    try:
        # Last 7 days daily counts
        days = []
        for i in range(6, -1, -1):
            day_start = (datetime.now() - timedelta(days=i)).replace(
                hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            count = db.query(Violation).filter(
                Violation.timestamp >= day_start,
                Violation.timestamp < day_end
            ).count()
            days.append({
                "date" : day_start.strftime("%a"),
                "count": count
            })

        # Per-camera breakdown
        cameras = db.query(
            Violation.camera_id,
            func.count(Violation.id).label('count')
        ).group_by(Violation.camera_id).all()

        # Per-PPE breakdown (all time)
        all_violations = db.query(Violation).all()
        ppe_counts = {}
        for v in all_violations:
            for item in (v.missing_ppe or []):
                ppe_counts[item] = ppe_counts.get(item, 0) + 1

        return {
            "daily"   : days,
            "by_camera": [{"camera": c, "count": n} for c, n in cameras],
            "by_ppe"  : [{"ppe": k, "count": v} for k, v in ppe_counts.items()],
        }
    finally:
        db.close()

@app.patch("/api/violations/{violation_id}/resolve")
def resolve_violation(violation_id: str, data: dict = {}):
    import uuid as _uuid
    from fastapi import HTTPException
    db = SessionLocal()
    try:
        # Validate UUID format before querying
        try:
            uid = _uuid.UUID(violation_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid violation ID format: {violation_id}"
            )

        row = db.query(Violation).filter(
            Violation.id == uid
        ).first()

        if not row:
            raise HTTPException(status_code=404, detail="Violation not found")

        row.resolved = True
        row.notes    = data.get("notes", "")
        db.commit()
        return {"success": True, "id": violation_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/source-mode")
def api_source_mode():
    return {
        "mode"    : SOURCE_MODE,
        "label"   : "Live RTSP Camera" if SOURCE_MODE == "rtsp" else "Pre-recorded File",
        "sources" : RTSP_SOURCES if SOURCE_MODE == "rtsp" else {"all": VIDEO_FILE}
    }