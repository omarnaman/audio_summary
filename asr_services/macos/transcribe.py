from asr_common.errors import TranscriptionError
from asr_common.types import Segment, TranscriptResult


def transcribe(wav_path: str, model: str) -> TranscriptResult:
    """Transcribe a WAV file using mlx-whisper. Imported lazily since mlx/mlx-whisper require
    Apple Silicon macOS with Metal and aren't installable elsewhere."""
    import mlx_whisper

    try:
        result = mlx_whisper.transcribe(wav_path, path_or_hf_repo=model)
    except Exception as e:
        raise TranscriptionError(f"mlx-whisper failed to transcribe '{wav_path}': {e}") from e

    segments = [
        Segment(start=float(seg["start"]), end=float(seg["end"]), text=str(seg["text"]).strip())
        for seg in result.get("segments", [])
    ]
    return TranscriptResult(segments=segments, language=result.get("language"))
