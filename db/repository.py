from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Conversion


def get_by_hash(session: Session, file_hash: str) -> Conversion | None:
    return session.get(Conversion, file_hash)


def list_all(session: Session) -> list[Conversion]:
    stmt = select(Conversion).order_by(Conversion.created_at.desc())
    return list(session.scalars(stmt))


def delete_by_hash(session: Session, file_hash: str) -> bool:
    conversion = session.get(Conversion, file_hash)
    if conversion is None:
        return False
    session.delete(conversion)
    session.flush()
    return True


def upsert(
    session: Session,
    *,
    hash: str,
    original_filename: str,
    title: str,
    filename_base: str,
    transcript_text: str,
    summary_text: str,
    whisper_model: str | None,
    diarization_model: str | None,
    summarization_model: str | None,
    transcribe_seconds: float | None,
    diarize_seconds: float | None,
    summarize_seconds: float | None,
    total_seconds: float | None,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
) -> Conversion:
    conversion = session.get(Conversion, hash)
    if conversion is None:
        conversion = Conversion(hash=hash)
        session.add(conversion)

    conversion.original_filename = original_filename
    conversion.title = title
    conversion.filename_base = filename_base
    conversion.transcript_text = transcript_text
    conversion.summary_text = summary_text
    conversion.whisper_model = whisper_model
    conversion.diarization_model = diarization_model
    conversion.summarization_model = summarization_model
    conversion.transcribe_seconds = transcribe_seconds
    conversion.diarize_seconds = diarize_seconds
    conversion.summarize_seconds = summarize_seconds
    conversion.total_seconds = total_seconds
    conversion.prompt_tokens = prompt_tokens
    conversion.completion_tokens = completion_tokens
    conversion.total_tokens = total_tokens

    session.flush()
    return conversion
