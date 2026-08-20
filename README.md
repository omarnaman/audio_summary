# Audio Summary

## Overview

A fully self-hostable audio/video summarizer. Upload any audio or video file and it will:

1. Convert it to WAV with `ffmpeg`.
2. Transcribe and diarize it (speaker labels) via a pluggable **ASR microservice** — two
   reference implementations live under `asr_services/`, split by platform:
   `asr_services/linux/` (`whisperx` + `pyannote.audio`, containerized, runs anywhere Docker
   runs) and `asr_services/macos/` (`mlx-whisper` + `pyannote.audio`, native macOS/Apple
   Silicon process for much faster Metal-accelerated inference). Both share their ffmpeg
   conversion, diarization, and error/data types via `asr_services/common/` (the `asr_common`
   package). You can also point it at your own service implementing the same HTTP contract.
3. Summarize the resulting transcript via any **OpenAI-compatible chat completions endpoint**
   (a local server such as llama.cpp, Ollama, vLLM, LM Studio — or a hosted one, if you want).
4. Persist the transcript, summary, and stats in **PostgreSQL** — point `DATABASE_URL` at
   whatever instance you already run in production (local, RDS, etc). A bundled Postgres
   container is included for local testing only, behind the `test` compose profile.

Nothing is required to leave your machine/network: no cloud transcription API, no cloud LLM API,
unless you choose to point the AI endpoint at one yourself.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- An OpenAI-compatible chat completions endpoint reachable from the `app` container (local or remote)
- (Only if using the bundled ASR service) a HuggingFace account + token, to accept the gated
  `pyannote/speaker-diarization` model terms once — see below

## Setup

1. **Clone the repository:**
   ```sh
   git clone <repository-url>
   cd audio_summary
   ```

2. **Create a `.env` file** in the project root:
   ```env
   # Postgres
   POSTGRES_PASSWORD=change-me
   DATABASE_URL=postgresql+psycopg://audio_summary:change-me@postgres:5432/audio_summary

   # OpenAI-compatible summarization endpoint
   AI_BASE_URL=http://host.docker.internal:11434/v1
   AI_API_KEY=not-needed
   AI_MODEL=llama3.1
   # Transcripts longer than this (in characters) are summarized map-reduce style:
   # summarized in chunks, then the chunk summaries are merged into a final summary.
   # This bounds the prefill size of any single LLM call, at the cost of extra calls
   # for long transcripts. Lower this if you're memory-constrained. Default: 20000.
   AI_SUMMARY_CHUNK_CHARS=20000

   # ASR (transcription + diarization) service
   ASR_SERVICE_URL=http://asr-service:8000
   # ASR_SERVICE_API_KEY=              # optional shared secret, only if the ASR service enforces one
   HF_TOKEN=hf_your_token_here          # only needed the first time, to download the gated diarization model
   ```

3. **Accept the pyannote model terms** (only if you're using the bundled ASR service): visit
   [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1) and
   [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0) on HuggingFace,
   accept their terms, and generate an access token for `HF_TOKEN` above. This is a one-time step —
   the weights are cached in a Docker volume afterwards and no further network access is needed.

## Running the Application

### Production

`docker compose up --build app` (optionally with `--profile default-asr` if you also want the
bundled ASR service) starts only the application — Postgres is **not** started by this compose
file by default, since a production deployment is expected to already have an instance running
(local, RDS, etc). Just point `DATABASE_URL` in `.env` at it.

### Local testing: bundled Postgres + whisperx/pyannote ASR service

The `postgres` service lives behind a `test` compose profile — it's a convenience for trying the
whole stack locally without standing up your own database first:

```sh
docker compose --profile test --profile default-asr up --build
```

This starts the app, a local Postgres container, and the reference ASR service (CPU-only
transcription — expect it to be noticeably slower than a native/GPU/Metal setup, but fully
functional and offline).

### Alternative: mlx-whisper on Apple Silicon (native, not containerized)

`asr_services/macos/` is a second reference implementation of the same ASR contract, using
[`mlx-whisper`](https://github.com/ml-explore/mlx-examples/tree/main/whisper) instead of
`whisperx` for transcription — much faster on Apple Silicon since it runs on Metal directly.
It **cannot run in Docker** (no Metal passthrough into containers, even on a Mac host), so it
runs as a native process on the Mac instead:

```sh
cd asr_services/macos
uv sync
uv run service.py
```

See `asr_services/macos/README.md` for full details. Then start the app in Docker, adding
`postgres` by name if you want the bundled local database too (naming it explicitly starts it
even though it's behind the `test` profile) — otherwise just point `DATABASE_URL` at your own:

```sh
docker compose up --build app postgres
```

...and set `ASR_SERVICE_URL=http://host.docker.internal:8000` in `.env` (assuming the app
container and the native mlx service are running on the same Mac).

### Using any other ASR service

More generally, you can point `ASR_SERVICE_URL` at anything implementing the same
`POST /transcribe` contract (see `asr_services/linux/service.py` for the exact request/response
shape) — then start just the app and Postgres:

```sh
docker compose up --build app postgres
```

### First-time database setup

Run migrations once (and again after pulling any future schema change):
```sh
docker compose exec app uv run alembic upgrade head
```

### Access the application

[http://localhost:5000](http://localhost:5000)

## Stopping the Application

```sh
docker compose down
```

## Command-line usage

`summarize_audio.py` runs the same pipeline without the web UI:
```sh
docker compose exec app uv run summarize_audio.py <path-to-audio-or-video> [--title "My Title"] [--force-rerun]
```

## TODO

- [ ] Extend with callbacks to be able to post summaries to a different notes app, e.g. obsidian or onenote
