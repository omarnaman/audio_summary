from asr_common.errors import DiarizationError
from asr_common.types import Segment, SpeakerTurn


def diarize(wav_path: str, model: str, hf_token: str | None) -> list[SpeakerTurn]:
    """Run speaker diarization on a WAV file using pyannote.audio. Imported lazily (heavy, torch-based)."""
    from pyannote.audio import Pipeline

    try:
        pipeline = Pipeline.from_pretrained(model, token=hf_token)
        annotation = pipeline(wav_path)
    except Exception as e:
        raise DiarizationError(f"pyannote failed to diarize '{wav_path}': {e}") from e

    return [
        SpeakerTurn(start=float(turn.start), end=float(turn.end), speaker=str(speaker))
        for turn, _, speaker in annotation.speaker_diarization.itertracks(yield_label=True)
    ]


def _format_timestamp(seconds: float) -> str:
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _overlap(seg: Segment, turn: SpeakerTurn) -> float:
    return max(0.0, min(seg.end, turn.end) - max(seg.start, turn.start))


def merge_segments(segments: list[Segment], turns: list[SpeakerTurn]) -> str:
    """Assign each transcript segment the speaker turn with maximum temporal overlap and
    format the result as a speaker-labeled, timestamped transcript."""
    lines = []
    for seg in segments:
        speaker = "UNKNOWN"
        best_overlap = 0.0
        for turn in turns:
            overlap = _overlap(seg, turn)
            if overlap > best_overlap:
                best_overlap = overlap
                speaker = turn.speaker
        lines.append(f"[{_format_timestamp(seg.start)} - {_format_timestamp(seg.end)}] {speaker}: {seg.text}")
    return "\n".join(lines)
