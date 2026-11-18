from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base


class Email(Base):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    message_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    subject: Mapped[str | None] = mapped_column(Text)
    sender: Mapped[str | None] = mapped_column(String(255), index=True)
    recipients: Mapped[dict | None] = mapped_column(JSONB)
    body_text: Mapped[str | None] = mapped_column(Text)
    body_html: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    thread_id: Mapped[str | None] = mapped_column(String(255), index=True)
    in_reply_to: Mapped[str | None] = mapped_column(String(255))
    headers: Mapped[dict | None] = mapped_column(JSONB)
    attachments: Mapped[dict | None] = mapped_column(JSONB)
    category: Mapped[str | None] = mapped_column(String(100), index=True)
    subcategory: Mapped[str | None] = mapped_column(String(100))
    tags: Mapped[list | None] = mapped_column(ARRAY(Text))
    priority: Mapped[int] = mapped_column(SmallInteger, default=0)
    language: Mapped[str] = mapped_column(String(10), default="zh")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    knowledge_entries: Mapped[list["KnowledgeEntry"]] = relationship(back_populates="email")


class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("emails.id"), index=True)
    question: Mapped[str | None] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100), index=True)
    tags: Mapped[list | None] = mapped_column(ARRAY(Text))
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    email: Mapped[Email | None] = relationship(back_populates="knowledge_entries")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    parent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categories.id"))
    description: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[list | None] = mapped_column(ARRAY(Text))
    level: Mapped[int] = mapped_column(SmallInteger, default=0)

    children: Mapped[list["Category"]] = relationship(back_populates="parent")
    parent: Mapped["Category | None"] = relationship(
        back_populates="children", remote_side=[id]
    )


class QueryLog(Base):
    __tablename__ = "query_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    query_text: Mapped[str | None] = mapped_column(Text)
    matched_ids: Mapped[list | None] = mapped_column(ARRAY(BigInteger))
    selected_id: Mapped[int | None] = mapped_column(BigInteger)
    feedback: Mapped[int | None] = mapped_column(SmallInteger)
    response_time_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
