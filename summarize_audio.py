#!/usr/bin/env python3
import argparse
import os
import sys

from config import load_config
from db.session import init_engine, session_scope
from pipeline.errors import PipelineError
from pipeline.run import process_upload


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe, diarize, and summarize an audio/video file using the configured "
        "ASR service and OpenAI-compatible summarization endpoint."
    )
    parser.add_argument("audio_path", help="Path to the audio/video file to summarize")
    parser.add_argument("--title", help="Optional title for the summary")
    parser.add_argument("--force-rerun", action="store_true", help="Reprocess even if a cached result exists")
    args = parser.parse_args()

    if not os.path.exists(args.audio_path):
        print(f"Error: File not found at '{args.audio_path}'")
        sys.exit(1)

    cfg = load_config()
    init_engine(cfg.database_url)

    try:
        with session_scope() as session:
            result = process_upload(
                args.audio_path,
                os.path.basename(args.audio_path),
                args.title,
                args.force_rerun,
                cfg,
                session,
            )
    except PipelineError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"--- {result.title} ---")
    print(result.content)
    print("------------------------")
    print(f"Reused from cache: {result.reused}")
    print(f"Stats: {result.stats}")


if __name__ == "__main__":
    main()
