import hashlib
import re


def calculate_sha256(filepath: str) -> str:
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def strip_heading_markers(text: str) -> str:
    return re.sub(r"^[#*\s]+", "", text).strip()


def slugify(title_text: str) -> str:
    title = re.sub(r"^[#*\s]+", "", title_text).strip()
    title = re.sub(r"[^\w\s-]", "", title)
    title = re.sub(r"[\s-]+", "_", title).lower()
    return title if title else "audio_summary"
