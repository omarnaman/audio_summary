import os
from dataclasses import dataclass

import requests

from config import Config
from pipeline.errors import AsrServiceError


@dataclass
class AsrResult:
    transcript: str
    language: str | None
    whisper_model: str | None
    diarization_model: str | None
    transcribe_seconds: float | None
    diarize_seconds: float | None


def transcribe_and_diarize(upload_path: str, cfg: Config) -> AsrResult:
    headers = {}
    if cfg.asr_service_api_key:
        headers["Authorization"] = f"Bearer {cfg.asr_service_api_key}"

    try:
        with open(upload_path, "rb") as f:
            response = requests.post(
                f"{cfg.asr_service_url}/transcribe",
                files={"audio": (os.path.basename(upload_path), f)},
                headers=headers,
                timeout=cfg.asr_service_timeout,
            )
    except requests.RequestException as e:
        raise AsrServiceError(f"Failed to reach ASR service at {cfg.asr_service_url}: {e}") from e

    if response.status_code != 200:
        try:
            message = response.json().get("error", response.text)
        except ValueError:
            message = response.text
        raise AsrServiceError(f"ASR service returned {response.status_code}: {message}")

    data = response.json()
    return AsrResult(
        transcript=data["transcript"],
        language=data.get("language"),
        whisper_model=data.get("whisper_model"),
        diarization_model=data.get("diarization_model"),
        transcribe_seconds=data.get("transcribe_seconds"),
        diarize_seconds=data.get("diarize_seconds"),
    )
