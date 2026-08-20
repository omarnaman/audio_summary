import wave

from asr_common.errors import DiarizationError
from asr_common.types import Segment, SpeakerTurn


def _load_waveform(wav_path: str):
    """Read a PCM WAV file directly (stdlib only) into a torch waveform tensor.

    convert.to_wav() always produces 16-bit PCM mono/stereo WAV, so this avoids
    handing pyannote.audio a file path, which it would otherwise decode via
    torchaudio/torchcodec - a dynamic-linking dependency on the host's FFmpeg
    shared libraries that has proven unreliable to set up correctly (e.g. on
    macOS, torchcodec's bundled dylibs can fail to locate Homebrew's FFmpeg
    libraries at runtime). Reading the WAV ourselves sidesteps that dependency
    entirely, on any platform.
    """
    import numpy as np
    import torch

    with wave.open(wav_path, "rb") as wf:
        sample_rate = wf.getframerate()
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        frames = wf.readframes(wf.getnframes())

    if sample_width != 2:
        raise DiarizationError(f"Unsupported WAV sample width {sample_width * 8}-bit (expected 16-bit PCM)")

    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).T
    else:
        samples = samples.reshape(1, -1)

    return torch.from_numpy(samples), sample_rate


def diarize(wav_path: str, model: str, hf_token: str | None) -> list[SpeakerTurn]:
    """Run speaker diarization on a WAV file using pyannote.audio. Imported lazily (heavy, torch-based)."""
    from pyannote.audio import Pipeline

    try:
        pipeline = Pipeline.from_pretrained(model, token=hf_token)
        waveform, sample_rate = _load_waveform(wav_path)
        annotation = pipeline({"waveform": waveform, "sample_rate": sample_rate})
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
