#!/usr/bin/env python3
import os
import shutil
import tempfile
import time

from flask import Flask, jsonify, request
from werkzeug.utils import secure_filename

import transcribe
from asr_common import convert, diarize
from asr_common.errors import AsrError
from config import load_config

app = Flask(__name__)
cfg = load_config()


def _unauthorized():
    if not cfg.api_key:
        return False
    auth_header = request.headers.get("Authorization", "")
    expected = f"Bearer {cfg.api_key}"
    return auth_header != expected


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/transcribe", methods=["POST"])
def transcribe_route():
    if _unauthorized():
        return jsonify({"error": "Unauthorized"}), 401

    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    if audio_file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    upload_dir = tempfile.mkdtemp(prefix="asr-upload-")
    upload_path = os.path.join(upload_dir, secure_filename(audio_file.filename))
    audio_file.save(upload_path)

    wav_path = None
    try:
        transcribe_start = time.time()
        wav_path = convert.to_wav(upload_path, cfg.ffmpeg_bin)
        transcript_result = transcribe.transcribe(
            wav_path, cfg.whisper_model, cfg.whisper_device, cfg.whisper_compute_type
        )
        transcribe_seconds = time.time() - transcribe_start

        diarize_start = time.time()
        turns = diarize.diarize(wav_path, cfg.diarization_model, cfg.hf_token)
        diarize_seconds = time.time() - diarize_start

        transcript_text = diarize.merge_segments(transcript_result.segments, turns)

        return jsonify({
            "transcript": transcript_text,
            "language": transcript_result.language,
            "whisper_model": cfg.whisper_model,
            "diarization_model": cfg.diarization_model,
            "transcribe_seconds": round(transcribe_seconds, 2),
            "diarize_seconds": round(diarize_seconds, 2),
        })
    except AsrError as e:
        return jsonify({"error": str(e)}), 500
    finally:
        shutil.rmtree(upload_dir, ignore_errors=True)
        if wav_path:
            shutil.rmtree(os.path.dirname(wav_path), ignore_errors=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=cfg.port)
