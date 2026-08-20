class AsrError(Exception):
    """Base class for all ASR service pipeline errors."""


class ConversionError(AsrError):
    """Raised when ffmpeg fails to convert the input file to WAV."""


class TranscriptionError(AsrError):
    """Raised when the Whisper backend fails to transcribe the audio."""


class DiarizationError(AsrError):
    """Raised when pyannote fails to diarize the audio."""
