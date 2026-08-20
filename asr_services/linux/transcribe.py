from asr_common.errors import TranscriptionError
from asr_common.types import Segment, TranscriptResult


def transcribe(wav_path: str, model: str, device: str, compute_type: str) -> TranscriptResult:
    """Transcribe a WAV file using whisperx. Imported lazily since whisperx/torch are heavy."""
    import whisperx

    try:
        asr_model = whisperx.load_model(model, device, compute_type=compute_type)
        audio = whisperx.load_audio(wav_path)
        result = asr_model.transcribe(audio, batch_size=16)
    except Exception as e:
        raise TranscriptionError(f"whisperx failed to transcribe '{wav_path}': {e}") from e

    segments = [
        Segment(start=float(seg["start"]), end=float(seg["end"]), text=str(seg["text"]).strip())
        for seg in result.get("segments", [])
    ]
    return TranscriptResult(segments=segments, language=result.get("language"))
