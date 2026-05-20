"""SQLAlchemy ORM models for inspection sessions and per-image findings."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InspectionSession(Base):
    __tablename__ = "inspection_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    created_by: Mapped[str] = mapped_column(String(320), default="", nullable=False)
    system_report_number: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    user_report_number: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    plant: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    system_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    preparer_name: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    reviewer_name: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    approver_name: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list["InspectionItem"]] = relationship(
        "InspectionItem",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="InspectionItem.sort_order",
    )


class InspectionItem(Base):
    __tablename__ = "inspection_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inspection_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    code: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    image_path: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    image_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    ai_findings: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_bounding_boxes_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    findings: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    rust_grade: Mapped[str | None] = mapped_column(String(8), nullable=True)
    cof: Mapped[int | None] = mapped_column(Integer, nullable=True)
    findings_priority: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sap_priority: Mapped[str | None] = mapped_column(String(16), nullable=True)
    equipment_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    equipment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    recommendation_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    further_inspection: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    open_insulation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scaffold: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_status: Mapped[str] = mapped_column(String(20), default="unreviewed", nullable=False)
    analysis_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    analysis_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    session: Mapped["InspectionSession"] = relationship("InspectionSession", back_populates="items")
