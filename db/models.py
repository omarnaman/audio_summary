from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Conversion(Base):
    __tablename__ = "conversions"

    hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    filename_base: Mapped[str] = mapped_column(String(512), nullable=False)

    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)
    summary_text: Mapped[str | None] = mapped_column(Text)

    whisper_model: Mapped[str | None] = mapped_column(String(255))
    diarization_model: Mapped[str | None] = mapped_column(String(255))
    summarization_model: Mapped[str | None] = mapped_column(String(255))

    transcribe_seconds: Mapped[float | None] = mapped_column(Float)
    diarize_seconds: Mapped[float | None] = mapped_column(Float)
    summarize_seconds: Mapped[float | None] = mapped_column(Float)
    total_seconds: Mapped[float | None] = mapped_column(Float)

    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
