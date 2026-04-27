"""
memory/job_store.py
SQLite-backed store for scraped jobs, application status, and deduplication.
Uses SQLAlchemy Core (no ORM overhead) for minimal footprint.
"""

import hashlib
import os
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    create_engine, MetaData, Table, Column,
    String, Float, DateTime, Boolean, Text, select, func
)
from dotenv import load_dotenv

load_dotenv()

DB_DIR = os.getenv("DB_DIR", "./data/dbs")


def _engine(user_id: str = "default"):
    # Ensure user_id is a string and safe for filenames
    safe_user_id = "".join([c for c in str(user_id) if c.isalnum() or c in ("-", "_")])
    if not safe_user_id:
        safe_user_id = "default"
    path = os.path.join(DB_DIR, f"jobs_{safe_user_id}.db")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return create_engine(f"sqlite:///{path}", echo=False)


metadata = MetaData()

jobs_table = Table("jobs", metadata,
    Column("id",          String(64),  primary_key=True),  # sha256 of url
    Column("portal",      String(32),  nullable=False),
    Column("title",       String(256), nullable=False),
    Column("company",     String(256)),
    Column("location",    String(256)),
    Column("url",         Text),
    Column("description", Text),
    Column("salary",      String(128)),
    Column("match_score", Float,    default=0.0),
    Column("scraped_at",  DateTime, default=datetime.utcnow),
    Column("applied",     Boolean,  default=False),
    Column("applied_at",  DateTime),
    Column("apply_status",String(64), default="pending"),  # pending/applied/failed/skipped
    Column("notes",       Text),
)


class JobStore:
    def __init__(self, user_id: str = "default"):
        self.engine = _engine(user_id)
        metadata.create_all(self.engine)

    @staticmethod
    def job_id(url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()[:32]

    def upsert_job(self, portal: str, title: str, company: str,
                   location: str, url: str, description: str = "",
                   salary: str = "", match_score: float = 0.0):
        jid = self.job_id(url)
        with self.engine.connect() as conn:
            existing = conn.execute(
                select(jobs_table).where(jobs_table.c.id == jid)
            ).fetchone()
            if existing:
                return jid, False   # already known
            conn.execute(jobs_table.insert().values(
                id=jid, portal=portal, title=title, company=company,
                location=location, url=url, description=description,
                salary=salary, match_score=match_score,
                scraped_at=datetime.utcnow(), applied=False,
                apply_status="pending",
            ))
            conn.commit()
        return jid, True   # new job

    def mark_applied(self, job_id: str, status: str = "applied", notes: str = ""):
        with self.engine.connect() as conn:
            conn.execute(
                jobs_table.update()
                .where(jobs_table.c.id == job_id)
                .values(applied=True, applied_at=datetime.utcnow(),
                        apply_status=status, notes=notes)
            )
            conn.commit()

    def get_pending(self, min_score: float = 0.65, limit: int = 50) -> list:
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(jobs_table)
                .where(jobs_table.c.applied == False)
                .where(jobs_table.c.match_score >= min_score)
                .where(jobs_table.c.apply_status == "pending")
                .order_by(jobs_table.c.match_score.desc())
                .limit(limit)
            ).fetchall()
        return [dict(r._mapping) for r in rows]

    def get_all(self, min_score: float = 0.0, limit: int = 300) -> list:
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(jobs_table)
                .where(jobs_table.c.match_score >= min_score)
                .order_by(jobs_table.c.match_score.desc())
                .limit(limit)
            ).fetchall()
        return [dict(r._mapping) for r in rows]

    def stats(self) -> dict:
        with self.engine.connect() as conn:
            total    = conn.execute(select(func.count()).select_from(jobs_table)).scalar()
            applied  = conn.execute(select(func.count()).select_from(jobs_table).where(jobs_table.c.applied == True)).scalar()
            pending  = conn.execute(select(func.count()).select_from(jobs_table).where(jobs_table.c.apply_status == "pending")).scalar()
        return {"total_scraped": total, "applied": applied, "pending": pending}

    def already_applied(self, url: str) -> bool:
        jid = self.job_id(url)
        with self.engine.connect() as conn:
            row = conn.execute(
                select(jobs_table.c.applied).where(jobs_table.c.id == jid)
            ).fetchone()
        return bool(row and row[0])