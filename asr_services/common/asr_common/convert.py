import os
import subprocess
import tempfile

from asr_common.errors import ConversionError


def to_wav(input_path: str, ffmpeg_bin: str = "ffmpeg") -> str:
    """Convert an arbitrary ffmpeg-readable audio/video file to a 16kHz mono PCM WAV file.

    Returns the path to the newly created WAV file (in a fresh temp directory).
    """
    out_dir = tempfile.mkdtemp(prefix="asr-wav-")
    out_path = os.path.join(out_dir, "audio.wav")

    result = subprocess.run(
        [ffmpeg_bin, "-y", "-i", input_path, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", out_path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ConversionError(f"ffmpeg failed to convert '{input_path}': {result.stderr.strip()}")

    return out_path
