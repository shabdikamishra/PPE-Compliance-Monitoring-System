import os
import uuid
import cv2
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ─────────────────────────────────────────────
#  Violation Event — one confirmed violation
# ─────────────────────────────────────────────

@dataclass
class ViolationEvent:
    id          : str
    camera_id   : str
    missing_ppe : List[str]
    detected_ppe: List[str]
    confidence  : float
    timestamp   : datetime
    image_path  : str = ""

    def to_dict(self):
        return {
            "id"          : self.id,
            "camera_id"   : self.camera_id,
            "missing_ppe" : self.missing_ppe,
            "detected_ppe": self.detected_ppe,
            "confidence"  : round(self.confidence, 3),
            "timestamp"   : self.timestamp.isoformat(),
            "image_path"  : self.image_path,
        }

# ─────────────────────────────────────────────
#  Violation Engine
# ─────────────────────────────────────────────

class ViolationEngine:
    """
    Processes each frame's detection results and decides
    whether to fire a violation alert.

    Two-layer filtering:
      1. Consecutive frame filter — PPE must be missing for
         `min_frames` frames in a row before an alert fires.
         This eliminates single-frame detection flickers.

      2. Cooldown timer — once an alert fires for a camera,
         no new alert is raised for `cooldown_seconds`.
         This prevents supervisor notification spam.
    """

    def __init__(
        self,
        cooldown_seconds : int = 30,
        min_frames       : int = 5,
        snapshot_dir     : str = "violations",
        required_ppe     : List[str] = None
    ):
        self.cooldown_seconds = cooldown_seconds
        self.min_frames       = min_frames
        self.snapshot_dir     = snapshot_dir
        self.required_ppe     = required_ppe or ['Hard_hat', 'Vest', 'Gloves','Safety_boots','Mask']

        # Per-camera state
        self._consecutive : Dict[str, int]      = {}   # consecutive missing frame count
        self._last_alert  : Dict[str, datetime] = {}   # last alert time per camera
        self._last_missing: Dict[str, List[str]]= {}   # what was missing last time

        # Full in-memory log
        self.violation_log: List[ViolationEvent] = []

        os.makedirs(self.snapshot_dir, exist_ok=True)
        print(f"[Engine] Initialized | cooldown={cooldown_seconds}s | min_frames={min_frames}")
        print(f"[Engine] Monitoring PPE: {self.required_ppe}")

    # ── Main method — call once per processed frame ───────────
    def process(
        self,
        camera_id        : str,
        detected_classes : List[str],
        frame            = None,
        avg_confidence   : float = 0.0
    ) -> Optional[ViolationEvent]:
        """
        Returns a ViolationEvent if a new violation is confirmed,
        otherwise returns None.
        """

        # What PPE is missing this frame?
        missing = [p for p in self.required_ppe if p not in detected_classes]
        detected_ppe = [p for p in self.required_ppe if p in detected_classes]

        # ── No violation this frame ───────────────────────────
        if not missing:
            self._consecutive[camera_id] = 0   # reset counter
            return None

        # ── Increment consecutive missing counter ─────────────
        self._consecutive[camera_id] = self._consecutive.get(camera_id, 0) + 1
        count = self._consecutive[camera_id]

        # ── Not enough consecutive frames yet ─────────────────
        if count < self.min_frames:
            return None   # could be a flicker — wait

        # ── Check cooldown ────────────────────────────────────
        now  = datetime.now()
        last = self._last_alert.get(camera_id)

        if last and (now - last) < timedelta(seconds=self.cooldown_seconds):
            remaining = self.cooldown_seconds - (now - last).seconds
            return None   # still in cooldown window

        # ── Valid violation — fire the alert ──────────────────
        self._last_alert[camera_id]   = now
        self._consecutive[camera_id]  = 0       # reset after alert fires
        self._last_missing[camera_id] = missing

        # Save snapshot
        image_path = self._save_snapshot(frame, camera_id, now)

        event = ViolationEvent(
            id           = str(uuid.uuid4()),
            camera_id    = camera_id,
            missing_ppe  = missing,
            detected_ppe = detected_ppe,
            confidence   = avg_confidence,
            timestamp    = now,
            image_path   = image_path,
        )

        self.violation_log.append(event)

        print(f"\n{'='*55}")
        print(f"  [VIOLATION FIRED] {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Camera    : {camera_id}")
        print(f"  Missing   : {missing}")
        print(f"  Detected  : {detected_ppe}")
        print(f"  Snapshot  : {image_path}")
        print(f"  Total logs: {len(self.violation_log)}")
        print(f"{'='*55}\n")

        return event

    # ── Save annotated snapshot to disk ───────────────────────
    def _save_snapshot(self, frame, camera_id: str, timestamp: datetime) -> str:
        if frame is None:
            return ""

        short_id  = str(uuid.uuid4())[:8]
        ts_str    = timestamp.strftime("%Y%m%d_%H%M%S")
        filename  = f"{camera_id}_{ts_str}_{short_id}.jpg"
        full_path = os.path.join(self.snapshot_dir, filename)

        cv2.imwrite(full_path, frame)
        return full_path

    # ── Status summary ────────────────────────────────────────
    def get_status(self, camera_id: str) -> dict:
        last = self._last_alert.get(camera_id)
        now  = datetime.now()

        if last:
            seconds_since = (now - last).seconds
            in_cooldown   = seconds_since < self.cooldown_seconds
            cooldown_left = max(0, self.cooldown_seconds - seconds_since)
        else:
            in_cooldown   = False
            cooldown_left = 0

        return {
            "camera_id"         : camera_id,
            "consecutive_frames": self._consecutive.get(camera_id, 0),
            "in_cooldown"       : in_cooldown,
            "cooldown_remaining": cooldown_left,
            "last_alert"        : last.isoformat() if last else None,
            "total_violations"  : len(self.violation_log),
        }

    # ── Summary of all violations so far ─────────────────────
    def summary(self):
        print(f"\n[Engine Summary]")
        print(f"  Total violations fired : {len(self.violation_log)}")
        for event in self.violation_log[-5:]:   # last 5
            print(f"  {event.timestamp.strftime('%H:%M:%S')} | {event.camera_id} | Missing: {event.missing_ppe}")