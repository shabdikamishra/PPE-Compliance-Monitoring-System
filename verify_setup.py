import sys
import os

# Load .env file
from dotenv import load_dotenv
load_dotenv()

DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "5432")
DB_NAME     = os.getenv("DB_NAME", "ppe_monitor")
DB_USER     = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

print("=" * 55)
print("  PPE Monitor — Phase 1 Verification")
print("=" * 55)

# ── 1. Python version ────────────────────────────────────────
print(f"\n[1] Python version: {sys.version.split()[0]}", end="  ")
if sys.version_info >= (3, 9):
    print("✓")
else:
    print("✗  Need Python 3.9+")

# ── 2. OpenCV ────────────────────────────────────────────────
try:
    import cv2
    print(f"[2] OpenCV: {cv2.__version__}  ✓")
except ImportError:
    print("[2] OpenCV: NOT FOUND  ✗  run: pip install opencv-python")

# ── 3. Ultralytics / YOLOv8 ──────────────────────────────────
try:
    from ultralytics import YOLO
    print(f"[3] Ultralytics: installed  ✓")
except ImportError:
    print("[3] Ultralytics: NOT FOUND  ✗  run: pip install ultralytics")

# ── 4. FastAPI + Uvicorn ─────────────────────────────────────
try:
    import fastapi, uvicorn
    print(f"[4] FastAPI: {fastapi.__version__}  |  Uvicorn: {uvicorn.__version__}  ✓")
except ImportError as e:
    print(f"[4] FastAPI/Uvicorn: NOT FOUND  ✗  {e}")

# ── 5. SQLAlchemy ─────────────────────────────────────────────
try:
    import sqlalchemy
    print(f"[5] SQLAlchemy: {sqlalchemy.__version__}  ✓")
except ImportError:
    print("[5] SQLAlchemy: NOT FOUND  ✗  run: pip install sqlalchemy")

# ── 6. Psycopg2 ──────────────────────────────────────────────
try:
    import psycopg2
    print(f"[6] psycopg2: installed  ✓")
except ImportError:
    print("[6] psycopg2: NOT FOUND  ✗  run: pip install psycopg2-binary")

# ── 7. python-dotenv ─────────────────────────────────────────
try:
    import dotenv
    print(f"[7] python-dotenv: installed  ✓")
except ImportError:
    print("[7] python-dotenv: NOT FOUND  ✗  run: pip install python-dotenv")

# ── 8. best.pt model file ────────────────────────────────────
model_path = "best.pt"
if os.path.exists(model_path):
    size_mb = os.path.getsize(model_path) / (1024 * 1024)
    print(f"[8] best.pt found ({size_mb:.1f} MB)  ✓")
else:
    print("[8] best.pt NOT FOUND  ✗  copy your trained model to project root")

# ── 9. Load model and print class names ──────────────────────
if os.path.exists(model_path):
    try:
        from ultralytics import YOLO
        print("\n[9] Loading model — please wait 10–20 seconds...")
        model = YOLO(model_path)
        print("\n╔══════════════════════════════════════════╗")
        print("║       YOUR MODEL'S CLASS NAMES           ║")
        print("╠══════════════════════════════════════════╣")
        for idx, name in model.names.items():
            print(f"║  {idx} : {name:<38}║")
        print("╚══════════════════════════════════════════╝")
        print("\n  *** Save these names — you will use them")
        print("  *** in violation_engine.py (Phase 3)")
    except Exception as e:
        print(f"[9] Model load FAILED  ✗  {e}")
else:
    print("[9] Skipping model load — best.pt not found")

# ── 10. .env file check ───────────────────────────────────────
print(f"\n[10] .env file check:")
print(f"     DB_HOST     = {DB_HOST}")
print(f"     DB_PORT     = {DB_PORT}")
print(f"     DB_NAME     = {DB_NAME}")
print(f"     DB_USER     = {DB_USER}")
print(f"     DB_PASSWORD = {'*' * len(DB_PASSWORD) if DB_PASSWORD else 'NOT SET ✗'}")

# ── 11. PostgreSQL connection ─────────────────────────────────
print(f"\n[11] Testing PostgreSQL connection...")
try:
    import psycopg2
    conn = psycopg2.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0].split(",")[0]
    cursor.close()
    conn.close()
    print(f"     Connected to: {DB_NAME}  ✓")
    print(f"     Server: {version}")
except Exception as e:
    print(f"     FAILED  ✗  {e}")
    print("     Make sure PostgreSQL is running and .env password is correct")

# ── Final summary ─────────────────────────────────────────────
print("\n" + "=" * 55)
print("  If all items show ✓ you are ready for Phase 2.")
print("=" * 55)