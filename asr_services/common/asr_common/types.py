from dataclasses import dataclass


@dataclass
class Segment:
    start: float
    end: float
    text: str


@dataclass
class TranscriptResult:
    segments: list[Segment]
    language: str | None


@dataclass
class SpeakerTurn:
    start: float
    end: float
    speaker: str
