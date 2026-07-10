from .database import SessionLocal, Violation

def save_violation(event):
    """
    Persist a ViolationEvent to the PostgreSQL violations table.
    Returns True on success, False on failure.
    """
    db = SessionLocal()
    try:
        record = Violation(
            camera_id    = event.camera_id,
            missing_ppe  = event.missing_ppe,
            detected_ppe = event.detected_ppe,
            confidence   = event.confidence,
            image_path   = event.image_path,
            timestamp    = event.timestamp,
        )
        db.add(record)
        db.commit()
        print(f"[DB] Violation saved → {record.id}")
        return True
    except Exception as e:
        db.rollback()
        print(f"[DB] Save failed: {e}")
        return False
    finally:
        db.close()


def get_recent_violations(limit=20):
    """Fetch most recent violations from DB."""
    db = SessionLocal()
    try:
        rows = (db.query(Violation)
                  .order_by(Violation.timestamp.desc())
                  .limit(limit)
                  .all())
        return rows
    finally:
        db.close()


def get_stats():
    """Return total and today's violation counts."""
    from datetime import datetime
    db = SessionLocal()
    try:
        total       = db.query(Violation).count()
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today       = db.query(Violation).filter(
                          Violation.timestamp >= today_start).count()
        return {"total": total, "today": today}
    finally:
        db.close()