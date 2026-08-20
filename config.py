import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _normalize_database_url(url: str) -> str:
    """Ensure the URL selects the psycopg (v3) driver we depend on.

    Managed Postgres providers (RDS, etc.) hand out plain postgres:// or
    postgresql:// connection strings, which SQLAlchemy defaults to the
    psycopg2 dialect for — a driver this project doesn't install.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


@dataclass(frozen=True)
class Config:
    database_url: str
    ai_base_url: str
    ai_api_key: str
    ai_model: str
    ai_summary_chunk_chars: int
    asr_service_url: str
    asr_service_api_key: str | None
    asr_service_timeout: int


def load_config() -> Config:
    missing = [
        name
        for name in ("DATABASE_URL", "AI_BASE_URL", "AI_MODEL", "ASR_SERVICE_URL")
        if not os.environ.get(name)
    ]
    if missing:
        raise RuntimeError(
            f"Missing required environment variable(s): {', '.join(missing)}. "
            "Set them in your .env file or environment."
        )

    return Config(
        database_url=_normalize_database_url(os.environ["DATABASE_URL"]),
        ai_base_url=os.environ["AI_BASE_URL"],
        ai_api_key=os.environ.get("AI_API_KEY", "not-needed"),
        ai_model=os.environ["AI_MODEL"],
        ai_summary_chunk_chars=int(os.environ.get("AI_SUMMARY_CHUNK_CHARS", "20000")),
        asr_service_url=os.environ["ASR_SERVICE_URL"].rstrip("/"),
        asr_service_api_key=os.environ.get("ASR_SERVICE_API_KEY") or None,
        asr_service_timeout=int(os.environ.get("ASR_SERVICE_TIMEOUT", "600")),
    )
