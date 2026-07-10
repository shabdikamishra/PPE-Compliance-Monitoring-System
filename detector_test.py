import cv2
from ultralytics import YOLO
import time
import os
import numpy as np
# Add these imports at the top of detector_test.py
from backend.database import init_db
from backend.violation_engine import ViolationEngine
from backend.db_writer import save_violation

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────

MODEL_PATH  = "best.pt"
VIDEO_PATH  = "test_video.mp4"

# PPE classes that mean equipment IS PRESENT
PRESENT_CLASSES = ['Gloves', 'Hard_hat', 'Mask', 'Person', 'Safety_boots', 'Vest']

# All PPE to monitor (shown in status panel)
ALL_PPE = [
    {'name': 'Hard_hat',     'label': 'Hard Hat'},
    {'name': 'Vest',         'label': 'Safety Vest'},
    {'name': 'Gloves',       'label': 'Gloves'},
    {'name': 'Mask',         'label' : 'Mask'},
    {'name': 'Safety_boots', 'label' : 'Safety Boots'}
]

# Box colors per class  (BGR format)
CLASS_COLORS = {
    'Hard_hat'     : (0,   200,   0),    # Green
    'Vest'         : (0,   200,   0),    # Green
    'Gloves'       : (0,   200,   0),    # Green
    'Mask'         : (0,   200,   0),    # Green
    'Safety_boots' : (0,   200,   0),    # Green
    'Person'       : (255, 165,   0),    # Orange
}
VIOLATION_BOX_COLOR = (0, 0, 220)        # Red for missing PPE context

CONFIDENCE      = 0.40
PROCESS_EVERY_N = 3

# ─────────────────────────────────────────────
#  LOAD MODEL
# ─────────────────────────────────────────────

print("Loading model...")
model = YOLO(MODEL_PATH)

# Initialize DB tables
init_db()

# Initialize violation engine
engine = ViolationEngine(
    cooldown_seconds = 30,
    min_frames       = 5,
    required_ppe     = PRESENT_CLASSES
)

print("\nModel class names:")
for idx, name in model.names.items():
    marker = "✓ (monitoring)" if name in PRESENT_CLASSES else "  "
    print(f"  {idx}: {name}  {marker}")

print(f"\nMonitoring PPE: {PRESENT_CLASSES}")
print("─" * 50)

# ─────────────────────────────────────────────
#  OPEN VIDEO
# ─────────────────────────────────────────────

cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    print(f"ERROR: Could not open '{VIDEO_PATH}'")
    exit()

fps          = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
width        = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print(f"Video: {width}x{height} @ {fps:.0f}fps  |  {total_frames} frames  |  {total_frames/fps:.1f}s")
print("Controls: Q = quit | S = save snapshot")
print("─" * 50)

# ─────────────────────────────────────────────
#  DRAWING HELPERS
# ─────────────────────────────────────────────

def draw_rounded_rect(img, pt1, pt2, color, thickness=2, radius=8):
    """Draw a rectangle with rounded corners."""
    x1, y1 = pt1
    x2, y2 = pt2
    # Sides
    cv2.line(img, (x1 + radius, y1), (x2 - radius, y1), color, thickness)
    cv2.line(img, (x1 + radius, y2), (x2 - radius, y2), color, thickness)
    cv2.line(img, (x1, y1 + radius), (x1, y2 - radius), color, thickness)
    cv2.line(img, (x2, y1 + radius), (x2, y2 - radius), color, thickness)
    # Corners
    cv2.ellipse(img, (x1+radius, y1+radius), (radius,radius), 180, 0, 90,  color, thickness)
    cv2.ellipse(img, (x2-radius, y1+radius), (radius,radius), 270, 0, 90,  color, thickness)
    cv2.ellipse(img, (x1+radius, y2-radius), (radius,radius), 90,  0, 90,  color, thickness)
    cv2.ellipse(img, (x2-radius, y2-radius), (radius,radius), 0,   0, 90,  color, thickness)

def draw_label(img, text, x, y, bg_color, text_color=(255,255,255), font_scale=0.55, thickness=1):
    """Draw a filled label tag above a bounding box."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    pad = 5
    cv2.rectangle(img, (x, y - th - pad*2), (x + tw + pad*2, y), bg_color, -1)
    cv2.putText(img, text, (x + pad, y - pad), font, font_scale, text_color, thickness, cv2.LINE_AA)

def draw_top_banner(img, is_violation, missing_ppe, frame_w):
    """Draw the top status banner."""
    banner_h = 56

    if is_violation:
        # Animated red — alternates intensity based on time
        pulse = int(abs(np.sin(time.time() * 3)) * 40)
        color = (0, 0, 180 + pulse)
        icon  = "!  VIOLATION DETECTED"
        detail = f"Missing PPE: {', '.join(missing_ppe)}"
    else:
        color  = (34, 139, 34)
        icon   = "✓  ALL PPE COMPLIANT"
        detail = "Worker is fully equipped"

    # Banner background
    cv2.rectangle(img, (0, 0), (frame_w, banner_h), color, -1)

    # Thin accent line at bottom of banner
    accent = (255, 255, 255) if is_violation else (144, 238, 144)
    cv2.line(img, (0, banner_h), (frame_w, banner_h), accent, 2)

    # Main status text
    cv2.putText(img, icon,
        (20, 30), cv2.FONT_HERSHEY_SIMPLEX,
        0.85, (255, 255, 255), 2, cv2.LINE_AA)

    # Detail text
    cv2.putText(img, detail,
        (20, 50), cv2.FONT_HERSHEY_SIMPLEX,
        0.48, (220, 220, 220), 1, cv2.LINE_AA)

    # Timestamp on the right
    ts = time.strftime("%H:%M:%S")
    cv2.putText(img, ts,
        (frame_w - 100, 30), cv2.FONT_HERSHEY_SIMPLEX,
        0.65, (200, 200, 200), 1, cv2.LINE_AA)

def draw_ppe_status_panel(img, detected_classes, frame_w, frame_h):
    """Draw a PPE checklist panel on the right side."""
    panel_w  = 210
    panel_h  = 30 + len(ALL_PPE) * 38 + 16
    margin   = 12
    x_start  = frame_w - panel_w - margin
    y_start  = 70

    # Panel background — semi-transparent dark
    overlay = img.copy()
    cv2.rectangle(overlay,
        (x_start - 10, y_start),
        (x_start + panel_w, y_start + panel_h),
        (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.75, img, 0.25, 0, img)

    # Panel title
    cv2.putText(img, "PPE STATUS",
        (x_start, y_start + 20),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55,
        (180, 180, 180), 1, cv2.LINE_AA)

    # Divider line
    cv2.line(img,
        (x_start - 10, y_start + 28),
        (x_start + panel_w, y_start + 28),
        (80, 80, 80), 1)

    # Each PPE item
    for i, ppe in enumerate(ALL_PPE):
        y = y_start + 50 + i * 38
        present = ppe['name'] in detected_classes

        # Status dot
        dot_color = (0, 210, 0) if present else (0, 0, 210)
        cv2.circle(img, (x_start + 8, y - 6), 7, dot_color, -1)

        # Status dot border
        cv2.circle(img, (x_start + 8, y - 6), 7, (255,255,255), 1)

        # PPE name
        cv2.putText(img, ppe['label'],
            (x_start + 24, y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.52,
            (240, 240, 240), 1, cv2.LINE_AA)

        # Status text
        status_text  = "Detected" if present else "NOT FOUND"
        status_color = (0, 210, 0) if present else (80, 80, 255)
        cv2.putText(img, status_text,
            (x_start + 24, y + 16),
            cv2.FONT_HERSHEY_SIMPLEX, 0.42,
            status_color, 1, cv2.LINE_AA)

def draw_bottom_bar(img, frame_count, violation_count, fps_actual, frame_w, frame_h):
    """Draw stats bar at the bottom."""
    bar_h = 32
    cv2.rectangle(img, (0, frame_h - bar_h), (frame_w, frame_h), (25, 25, 25), -1)
    cv2.line(img, (0, frame_h - bar_h), (frame_w, frame_h - bar_h), (70, 70, 70), 1)

    stats = f"  Frame: {frame_count}   |   Violations: {violation_count}   |   FPS: {fps_actual:.1f}   |   CAM: CAM_01   |   PPE Monitor v1.0"
    cv2.putText(img, stats,
        (10, frame_h - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45, (160, 160, 160), 1, cv2.LINE_AA)

def draw_custom_boxes(img, results, model_names):
    """Draw custom bounding boxes instead of YOLOv8 default."""
    for box in results.boxes:
        cls_id     = int(box.cls)
        cls_name   = model_names[cls_id]
        conf       = float(box.conf)
        x1, y1, x2, y2 = map(int, box.xyxy[0])

        color = CLASS_COLORS.get(cls_name, (200, 200, 200))

        # Draw rounded bounding box
        draw_rounded_rect(img, (x1, y1), (x2, y2), color, thickness=2, radius=6)

        # Draw corner accents for a techy look
        corner_len = 14
        thick = 3
        # Top-left
        cv2.line(img, (x1, y1), (x1 + corner_len, y1), color, thick)
        cv2.line(img, (x1, y1), (x1, y1 + corner_len), color, thick)
        # Top-right
        cv2.line(img, (x2, y1), (x2 - corner_len, y1), color, thick)
        cv2.line(img, (x2, y1), (x2, y1 + corner_len), color, thick)
        # Bottom-left
        cv2.line(img, (x1, y2), (x1 + corner_len, y2), color, thick)
        cv2.line(img, (x1, y2), (x1, y2 - corner_len), color, thick)
        # Bottom-right
        cv2.line(img, (x2, y2), (x2 - corner_len, y2), color, thick)
        cv2.line(img, (x2, y2), (x2, y2 - corner_len), color, thick)

        # Label tag
        label = f"{cls_name}  {conf:.2f}"
        draw_label(img, label, x1, y1, color)

# ─────────────────────────────────────────────
#  MAIN DETECTION LOOP
# ─────────────────────────────────────────────

frame_count     = 0
violation_count = 0
start_time      = time.time()
last_annotated  = None

os.makedirs("violations", exist_ok=True)

while cap.isOpened():

    ret, frame = cap.read()

    if not ret:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        continue

    frame_count += 1

    if frame_count % PROCESS_EVERY_N != 0:
        # Show last annotated frame to keep display smooth
        if last_annotated is not None:
            cv2.imshow("PPE Compliance Monitor", last_annotated)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        continue

    # ── Resize ────────────────────────────────────────────────
    display = cv2.resize(frame, (960, 540))
    frame_h, frame_w = display.shape[:2]

    # ── Run detection (get raw results, don't use .plot()) ────
    results          = model(display, conf=CONFIDENCE, verbose=False)[0]
    detected_classes = [model.names[int(b.cls)] for b in results.boxes]


   # Run through violation engine
avg_conf = float(sum(float(b.conf) for b in results.boxes) / len(results.boxes)) \
           if results.boxes else 0.0

event = engine.process(
    camera_id        = "CAM_01",
    detected_classes = detected_classes,
    frame            = annotated,    # saves annotated snapshot
    avg_confidence   = avg_conf
)

# For display purposes — show missing PPE on banner every frame
missing_ppe  = [p for p in PRESENT_CLASSES if p not in detected_classes]
is_violation = len(missing_ppe) > 0

# Only count + save to DB when engine fires a confirmed event
if event:
    violation_count += 1
    save_violation(event)

    # ── Build annotated frame from scratch ────────────────────
    annotated = display.copy()

    # Draw custom bounding boxes (replaces results.plot())
    draw_custom_boxes(annotated, results, model.names)

    # Draw UI elements
    draw_top_banner(annotated, is_violation, missing_ppe, frame_w)
    draw_ppe_status_panel(annotated, detected_classes, frame_w, frame_h)

    elapsed    = time.time() - start_time
    actual_fps = (frame_count / PROCESS_EVERY_N) / elapsed if elapsed > 0 else 0
    draw_bottom_bar(annotated, frame_count, violation_count, actual_fps, frame_w, frame_h)

    # ── Console log ───────────────────────────────────────────
    if is_violation:
        print(f"[{time.strftime('%H:%M:%S')}] VIOLATION | Missing: {missing_ppe} | Detected: {detected_classes}")

    last_annotated = annotated
    cv2.imshow("PPE Compliance Monitor", annotated)

    # ── Key controls ──────────────────────────────────────────
    key = cv2.waitKey(1) & 0xFF

    if key == ord('q'):
        print("Quit.")
        break

    elif key == ord('s'):
        ts        = int(time.time())
        save_path = f"violations/snapshot_{ts}.jpg"
        cv2.imwrite(save_path, annotated)
        print(f"Snapshot saved → {save_path}")

# ─────────────────────────────────────────────
#  CLEANUP
# ─────────────────────────────────────────────

cap.release()
cv2.destroyAllWindows()

elapsed = time.time() - start_time
print("\n" + "=" * 50)
print(f"  Frames processed : {frame_count}")
print(f"  Violations found : {violation_count}")
print(f"  Duration         : {elapsed:.1f}s")
print("=" * 50)