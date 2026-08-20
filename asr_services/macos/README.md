# asr-service-macos

An alternative reference implementation of the `audio_summary` ASR microservice contract
(see `../linux/service.py` for the containerized `whisperx` reference), using
[`mlx-whisper`](https://github.com/ml-explore/mlx-examples/tree/main/whisper) for
transcription instead — Apple's MLX framework runs directly on Metal, so this is
significantly faster than CPU-based `whisperx` on Apple Silicon hardware. Diarization
first attempts [`mlx-audio`](https://github.com/Blaizzy/mlx-audio)'s Sortformer model
(also MLX/Metal-native, so likewise faster than CPU-based diarization), falling back to
the shared `pyannote.audio`-based implementation from `asr_common` if `mlx-audio`/Sortformer
is unavailable or fails at runtime. ffmpeg conversion is shared with the other
implementation through the `asr_common` package in `../common/`.

## Why this isn't containerized

`mlx-whisper` depends on Apple's MLX framework, which talks to Metal directly. Docker
containers — even on an Apple Silicon Mac host — run inside a Linux VM with no GPU/Metal
passthrough, so `mlx-whisper` **cannot run inside a container at all**, on any platform.
This service is meant to run as a **native process directly on macOS** (Apple Silicon
required), alongside the rest of the stack running in Docker.

## Requirements

- macOS on Apple Silicon (M1/M2/M3/M4)
- `ffmpeg` on `PATH` (`brew install ffmpeg`)
- Python 3.10–3.13 (pyannote.audio's `torch` dependency doesn't yet ship wheels for newer
  versions) — `uv` will use the pinned `.python-version` (3.13) automatically
- A HuggingFace token with the `pyannote/speaker-diarization-3.1` and
  `pyannote/segmentation-3.0` model terms accepted, for the one-time gated diarization
  model download (see the root README)

## Running

```sh
cd asr_services/macos
uv sync
uv run service.py
```

By default this listens on `0.0.0.0:8000` and implements the same `POST /transcribe` /
`GET /health` contract as the Docker-based reference service. Point the main app at it by
setting, in the main app's `.env`:

```env
ASR_SERVICE_URL=http://host.docker.internal:8000
```

(assuming the main app is running in Docker on the same Mac; use the Mac's LAN address
instead if the app is running on a different machine).

## Configuration

| Var | Required | Default |
|---|---|---|
| `WHISPER_MODEL` | no | `mlx-community/whisper-large-v3-turbo` (any `mlx-community` Whisper repo) |
| `SORTFORMER_MODEL` | no | `mlx-community/diar_sortformer_4spk-v1-fp16` (mlx-audio Sortformer diarization model, tried first) |
| `DIARIZATION_MODEL` | no | `pyannote/speaker-diarization-3.1` (pyannote.audio fallback, used only if the Sortformer attempt above fails) |
| `HF_TOKEN` | no | none (only needed for the first gated model download — applies to both the pyannote fallback and Sortformer's HF-hosted weights) |
| `FFMPEG_BIN` | no | `ffmpeg` |
| `API_KEY` | no | none (if set, requires a matching `Authorization: Bearer` header) |
| `PORT` | no | `8000` |

## Note on this build environment

This service was written and code-reviewed but **could not be installed or run** in the
session that built it, since that environment was Linux, not Apple Silicon macOS —
`mlx-whisper`'s native `mlx` dependency has no functioning Linux build at all (its wheel
installs on Linux but `import mlx.core` fails with a missing shared library, unlike
`whisperx`/`torch`, which fully install and run on Linux). It shares `convert.py`,
`errors.py`, and `types.py`, plus the pyannote.audio fallback implementation in
`asr_common/diarize.py`, with `../linux/` via the `asr_common` package, which *was* fully
tested in that environment (real ffmpeg conversion, real whisperx transcription, real
pyannote.audio pipeline construction) — only `transcribe.py`'s `mlx_whisper.transcribe(...)`
call, this directory's own `diarize.py`'s `mlx-audio` Sortformer attempt, and the overall
service on real hardware need first-run verification on an actual Mac. `mlx-audio`, like
`mlx`/`mlx-whisper`, could not be installed or exercised in this session either, for the
same reason (no Metal on Linux) — the pyannote.audio fallback path is the one piece that
*is* exercised by `asr_common`'s existing (Linux-tested) coverage, since it's the same code
`../linux/` already runs.
