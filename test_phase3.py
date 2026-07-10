"""
Phase 3 verification script.
Tests violation engine logic and database connection independently.
Run: python test_phase3.py
"""

import sys
import time
from datetime import datetime

print("=" * 55)
print("  PPE Monitor — Phase 3 Verification")
print("=" * 55)

# ── 1. Database connection ────────────────────────────────────
print("\n[1] Testing database connection and table creation...")
try:
    from backend.database import init_db, engine
    init_db()
    print("    ✓ Connected and tables created")
except Exception as e:
    print(f"    ✗ Database error: {e}")
    sys.exit(1)

# ── 2. Violation engine — no violation scenario ───────────────
print("\n[2] Testing engine — all PPE present (should return None)...")
from backend.violation_engine import ViolationEngine

engine_test = ViolationEngine(
    cooldown_seconds=30,
    min_frames=5,
    required_ppe=['Hard_hat', 'Vest', 'Gloves','Safety_boots','Mask']
)

result = engine_test.process(
    camera_id="CAM_TEST",
    detected_classes=['Hard_hat', 'Vest', 'Gloves','Safety_boots','Mask','Person'],
)
assert result is None, "Should return None when all PPE present"
print("    ✓ No violation when all PPE present")

# ── 3. Violation engine — consecutive frame filter ────────────
print("\n[3] Testing consecutive frame filter (need 5 frames)...")
for i in range(4):
    result = engine_test.process(
        camera_id="CAM_TEST",
        detected_classes=['Person'],   # missing all PPE
    )
    assert result is None, f"Should not fire before min_frames (frame {i+1})"
    print(f"    Frame {i+1}/4 — no alert yet (correct)")

print("    ✓ Consecutive filter working correctly")

# ── 4. Violation engine — violation fires on 5th frame ────────
print("\n[4] Testing violation fires on 5th consecutive frame...")
result = engine_test.process(
    camera_id="CAM_TEST",
    detected_classes=['Person'],
    avg_confidence=0.82
)
assert result is not None, "Should fire on 5th frame"
assert 'Hard_hat' in result.missing_ppe
assert result.camera_id == "CAM_TEST"
print(f"    ✓ Violation fired correctly")
print(f"    Missing PPE : {result.missing_ppe}")
print(f"    Event ID    : {result.id}")

# ── 5. Cooldown test ──────────────────────────────────────────
print("\n[5] Testing cooldown — 2nd alert should be suppressed...")
for i in range(10):
    result = engine_test.process(
        camera_id="CAM_TEST",
        detected_classes=['Person'],
    )
assert result is None, "Should be suppressed during cooldown"
print("    ✓ Cooldown working — duplicate alert suppressed")

# ── 6. Save violation to database ────────────────────────────
print("\n[6] Saving a test violation to PostgreSQL...")
try:
    from backend.violation_engine import ViolationEvent
    from backend.db_writer import save_violation, get_stats

    test_event = ViolationEvent(
        id           = "test-001",
        camera_id    = "CAM_TEST",
        missing_ppe  = ["Hard_hat", "Gloves","Mask"],
        detected_ppe = ["Vest","Safety_boots"],
        confidence   = 0.87,
        timestamp    = datetime.now(),
        image_path   = ""
    )

    success = save_violation(test_event)
    assert success, "DB save returned False"
    print("    ✓ Violation saved to database")
except Exception as e:
    print(f"    ✗ DB save error: {e}")
    sys.exit(1)

# ── 7. Read back from database ────────────────────────────────
print("\n[7] Reading violations back from database...")
try:
    from backend.db_writer import get_recent_violations
    rows = get_recent_violations(limit=5)
    print(f"    ✓ Found {len(rows)} violation(s) in DB")
    for row in rows:
        print(f"      → {row.camera_id} | {row.missing_ppe} | {row.timestamp.strftime('%H:%M:%S')}")
except Exception as e:
    print(f"    ✗ DB read error: {e}")

# ── 8. Stats ──────────────────────────────────────────────────
print("\n[8] Checking stats...")
try:
    from backend.db_writer import get_stats
    stats = get_stats()
    print(f"    ✓ Total violations in DB : {stats['total']}")
    print(f"    ✓ Today's violations     : {stats['today']}")
except Exception as e:
    print(f"    ✗ Stats error: {e}")

print("\n" + "=" * 55)
print("  Phase 3 verification complete.")
print("  If all items show ✓ you are ready for Phase 4.")
print("=" * 55)