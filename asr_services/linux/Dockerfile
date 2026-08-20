# Build context is asr_services/ (the parent of this directory), so that ../common
# (the shared asr_common path dependency) is available to COPY.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

# System dependencies: ffmpeg for audio/video conversion, build tools for torch/pyannote wheels
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg build-essential \
    && rm -rf /var/lib/apt/lists/*

# Shared asr_common package (path dependency)
COPY common/ ./common/

# Sync uv requirements
COPY linux/pyproject.toml linux/uv.lock ./linux/
WORKDIR /app/linux
RUN uv sync --no-dev

# Copy the rest of the service's code into the container
COPY linux/ .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run service.py when the container launches
CMD ["uv", "run", "service.py"]
