import os
import uuid
from datetime import datetime

from sqlalchemy import create_engine, Column, String, DateTime, Float, Text, Boolean
from sqlalchemy import create_engine, Column, String, DateTime, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from dotenv import load_dotenv

load_dotenv()

# ── Build connection URL from .env ────────────────────────────
DB_HOST     = os.getenv("DB_HOST",     "localhost")
DB_PORT     = os.getenv("DB_PORT",     "5432")
DB_NAME     = os.getenv("DB_NAME",     "ppe_monitor")
DB_USER     = os.getenv("DB_USER",     "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ── SQLAlchemy setup ──────────────────────────────────────────
engine       = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base         = declarative_base()

# ── Violations table ──────────────────────────────────────────
class Violation(Base):
    __tablename__ = "violations"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_id    = Column(String(50),  nullable=False, default="CAM_01")
    missing_ppe  = Column(ARRAY(String), nullable=False)
    detected_ppe = Column(ARRAY(String), nullable=False, default=[])
    confidence   = Column(Float,         nullable=False, default=0.0)
    image_path   = Column(Text,          nullable=False, default="")
    timestamp    = Column(DateTime,      nullable=False, default=datetime.utcnow)
    resolved     = Column(Boolean,       nullable=False, default=False)   
    notes        = Column(Text,          nullable=True,  default="")      

    def __repr__(self):
        return (f"<Violation id={self.id} "
                f"camera={self.camera_id} "
                f"missing={self.missing_ppe} "
                f"time={self.timestamp}>")

# ── Create all tables on startup ──────────────────────────────
def init_db():
    Base.metadata.create_all(engine)
    print("[DB] Tables created / verified ✓")

# ── Helper to get a DB session ────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()