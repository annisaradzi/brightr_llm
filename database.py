"""SQLAlchemy engine and session factory for brightr inspection persistence."""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./brightr.db").strip()

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()


def init_db() -> None:
    from models import InspectionItem, InspectionSession  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_session_columns()


def _ensure_session_columns() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return

    expected = {
        "system_report_number": "TEXT",
        "user_report_number": "TEXT",
        "plant": "TEXT",
        "system_code": "TEXT",
        "preparer_name": "TEXT",
        "reviewer_name": "TEXT",
        "approver_name": "TEXT",
        "executive_summary": "TEXT",
        "pdf_path": "TEXT",
        "updated_at": "DATETIME",
        "reviewed_at": "DATETIME",
        "approved_at": "DATETIME",
        "review_comment": "TEXT",
    }
    idx_expected = {
        "ix_inspection_sessions_system_report_number": "system_report_number",
        "ix_inspection_sessions_user_report_number": "user_report_number",
        "ix_inspection_sessions_plant": "plant",
        "ix_inspection_sessions_system_code": "system_code",
        "ix_inspection_sessions_preparer_name": "preparer_name",
        "ix_inspection_sessions_reviewer_name": "reviewer_name",
        "ix_inspection_sessions_approver_name": "approver_name",
    }

    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("inspection_sessions")}
    with engine.begin() as conn:
        for name, col_type in expected.items():
            if name not in cols:
                conn.execute(text(f"ALTER TABLE inspection_sessions ADD COLUMN {name} {col_type}"))
        for idx_name, col_name in idx_expected.items():
            conn.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS {idx_name} ON inspection_sessions ({col_name})"
                )
            )


@contextmanager
def db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
