import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    whisper_model: str
    diarization_model: str
    hf_token: str | None
    ffmpeg_bin: str
    api_key: str | None
    port: int


def load_config() -> Config:
    return Config(
        whisper_model=os.environ.get("WHISPER_MODEL", "mlx-community/whisper-large-v3-turbo"),
        diarization_model=os.environ.get("DIARIZATION_MODEL", "pyannote/speaker-diarization-3.1"),
        hf_token=os.environ.get("HF_TOKEN") or None,
        ffmpeg_bin=os.environ.get("FFMPEG_BIN", "ffmpeg"),
        api_key=os.environ.get("API_KEY") or None,
        port=int(os.environ.get("PORT", "8000")),
    )
