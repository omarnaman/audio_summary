import time
from dataclasses import dataclass

from sqlalchemy.orm import Session

from config import Config
from db import repository
from db.models import Conversion
from pipeline import asr_client, hashing, summarize


@dataclass
class PipelineResult:
    hash: str
    title: str
    filename_base: str
    date: str
    transcript: str
    content: str
    stats: dict
    reused: bool


def _from_model(conversion: Conversion, reused: bool) -> PipelineResult:
    return PipelineResult(
        hash=conversion.hash,
        title=conversion.title,
        filename_base=conversion.filename_base,
        date=conversion.created_at.date().isoformat(),
        transcript=conversion.transcript_text,
        content=conversion.summary_text,
        stats={
            "transcribe_seconds": conversion.transcribe_seconds,
            "diarize_seconds": conversion.diarize_seconds,
            "summarize_seconds": conversion.summarize_seconds,
            "total_seconds": conversion.total_seconds,
            "prompt_tokens": conversion.prompt_tokens,
            "completion_tokens": conversion.completion_tokens,
            "total_tokens": conversion.total_tokens,
        },
        reused=reused,
    )


def process_upload(
    upload_path: str,
    original_filename: str,
    user_title: str | None,
    force_rerun: bool,
    cfg: Config,
    session: Session,
) -> PipelineResult:
    file_hash = hashing.calculate_sha256(upload_path)
    existing = repository.get_by_hash(session, file_hash)
    if existing and existing.summary_text and not force_rerun:
        return _from_model(existing, reused=True)

    total_start = time.time()

    if existing and existing.transcript_text and not force_rerun:
        # A prior run already transcribed this file but never got a summary
        # (LLM failure, or it's being retried with a different model) - reuse
        # the saved transcript instead of re-running ASR.
        transcript = existing.transcript_text
        whisper_model = existing.whisper_model
        diarization_model = existing.diarization_model
        transcribe_seconds = existing.transcribe_seconds
        diarize_seconds = existing.diarize_seconds
    else:
        asr = asr_client.transcribe_and_diarize(upload_path, cfg)
        transcript = asr.transcript
        whisper_model = asr.whisper_model
        diarization_model = asr.diarization_model
        transcribe_seconds = asr.transcribe_seconds
        diarize_seconds = asr.diarize_seconds

        repository.save_transcript(
            session,
            hash=file_hash,
            original_filename=original_filename,
            title=user_title or original_filename,
            filename_base=hashing.slugify(user_title or original_filename),
            transcript_text=transcript,
            whisper_model=whisper_model,
            diarization_model=diarization_model,
            transcribe_seconds=transcribe_seconds,
            diarize_seconds=diarize_seconds,
        )
        # Commit now so the transcript survives even if summarization fails below.
        session.commit()

    summarize_start = time.time()
    summary = summarize.summarize(transcript, cfg)
    summarize_seconds = time.time() - summarize_start

    total_seconds = time.time() - total_start

    if user_title:
        title = user_title
    else:
        title_line = next((line.strip() for line in summary.markdown.strip().split("\n") if line.strip()), "Detailed Summary")
        title = hashing.strip_heading_markers(title_line)

    filename_base = hashing.slugify(title)

    conversion = repository.save_summary(
        session,
        hash=file_hash,
        title=title,
        filename_base=filename_base,
        summary_text=summary.markdown,
        summarization_model=cfg.ai_model,
        summarize_seconds=round(summarize_seconds, 2),
        total_seconds=round(total_seconds, 2),
        prompt_tokens=summary.prompt_tokens,
        completion_tokens=summary.completion_tokens,
        total_tokens=summary.total_tokens,
    )

    return _from_model(conversion, reused=False)
