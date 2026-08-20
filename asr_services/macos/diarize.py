import logging

from asr_common import diarize as _pyannote
from asr_common.types import SpeakerTurn

logger = logging.getLogger(__name__)


def _diarize_sortformer(wav_path: str, model: str) -> list[SpeakerTurn]:
    """Diarize using mlx-audio's Sortformer model. Imported lazily since mlx/mlx-audio require
    Apple Silicon macOS with Metal and aren't installable elsewhere."""
    from mlx_audio.vad import load

    sortformer = load(model)
    result = sortformer.generate(wav_path)
    return [
        SpeakerTurn(start=float(seg.start), end=float(seg.end), speaker=str(seg.speaker))
        for seg in result.segments
    ]


def diarize(wav_path: str, sortformer_model: str, pyannote_model: str, hf_token: str | None) -> list[SpeakerTurn]:
    """Diarize using mlx-audio's Sortformer (Metal-native, fast), falling back to the shared
    pyannote.audio implementation if Sortformer is unavailable or fails."""
    try:
        return _diarize_sortformer(wav_path, sortformer_model)
    except Exception as e:
        logger.warning("mlx-audio Sortformer diarization failed (%s); falling back to pyannote.audio", e)
    return _pyannote.diarize(wav_path, pyannote_model, hf_token)
