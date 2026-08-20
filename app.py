#!/usr/bin/env python3
import tempfile
import threading
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

from config import load_config
from db import repository
from db.session import init_engine, session_scope
from db.models import Conversion
from pipeline.errors import PipelineError
from pipeline.jobs import complete_job, create_job, fail_job, get_job, update_job
from pipeline.run import process_upload, reinvoke_summary

app = Flask(__name__)
cfg = load_config()
init_engine(cfg.database_url)


def _conversion_to_list_item(conversion: Conversion) -> dict:
    return {
        "hash": conversion.hash,
        "title": conversion.title,
        "filename_base": conversion.filename_base,
        "original_filename": conversion.original_filename,
        "date": conversion.created_at.date().isoformat(),
        "has_summary": conversion.summary_text is not None,
        "stats": {
            "transcribe_seconds": conversion.transcribe_seconds,
            "diarize_seconds": conversion.diarize_seconds,
            "summarize_seconds": conversion.summarize_seconds,
            "total_seconds": conversion.total_seconds,
            "prompt_tokens": conversion.prompt_tokens,
            "completion_tokens": conversion.completion_tokens,
            "total_tokens": conversion.total_tokens,
        },
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/conversions", methods=["GET"])
def get_conversions():
    with session_scope() as session:
        conversions = repository.list_all(session)
        return jsonify([_conversion_to_list_item(c) for c in conversions])


@app.route("/api/conversions/<file_hash>", methods=["GET"])
def get_conversion_content(file_hash):
    with session_scope() as session:
        conversion = repository.get_by_hash(session, file_hash)
        if not conversion:
            return jsonify({"error": "Conversion not found"}), 404
        return jsonify({
            "content": conversion.summary_text,
            "transcript": conversion.transcript_text,
            "has_summary": conversion.summary_text is not None,
        })


@app.route("/api/conversions/<file_hash>", methods=["DELETE"])
def delete_conversion(file_hash):
    with session_scope() as session:
        deleted = repository.delete_by_hash(session, file_hash)
        if not deleted:
            return jsonify({"error": "Conversion not found"}), 404
        return jsonify({"message": "Conversion deleted successfully"})


def _result_to_payload(result) -> dict:
    return {
        "hash": result.hash,
        "title": result.title,
        "filename_base": result.filename_base,
        "date": result.date,
        "content": result.content,
        "transcript": result.transcript,
        "stats": result.stats,
        "reused": result.reused,
    }


@app.route("/api/convert", methods=["POST"])
def convert_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    if audio_file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    original_filename = audio_file.filename
    force_rerun = request.form.get("force_rerun", "false").lower() == "true"
    user_title = request.form.get("title", "").strip() or None

    upload_dir = tempfile.mkdtemp(prefix="audio-summary-upload-")
    upload_path = str(Path(upload_dir, secure_filename(original_filename)))
    audio_file.save(upload_path)

    job_id = create_job()

    def run_job():
        def on_progress(stage, message):
            update_job(job_id, stage, message)

        try:
            with session_scope() as session:
                result = process_upload(
                    upload_path, original_filename, user_title, force_rerun, cfg, session, on_progress=on_progress
                )
            complete_job(job_id, _result_to_payload(result))
        except PipelineError as e:
            fail_job(job_id, str(e))
        finally:
            Path(upload_path).unlink(missing_ok=True)
            Path(upload_dir).rmdir()

    threading.Thread(target=run_job, daemon=True).start()
    return jsonify({"job_id": job_id}), 202


@app.route("/api/conversions/<file_hash>/summarize", methods=["POST"])
def resummarize_conversion(file_hash):
    user_title = request.form.get("title", "").strip() or None

    job_id = create_job()

    def run_job():
        def on_progress(stage, message):
            update_job(job_id, stage, message)

        try:
            with session_scope() as session:
                result = reinvoke_summary(file_hash, user_title, cfg, session, on_progress=on_progress)
            complete_job(job_id, _result_to_payload(result))
        except PipelineError as e:
            fail_job(job_id, str(e))

    threading.Thread(target=run_job, daemon=True).start()
    return jsonify({"job_id": job_id}), 202


@app.route("/api/jobs/<job_id>", methods=["GET"])
def get_job_status(job_id):
    job = get_job(job_id)
    if job is None:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({
        "status": job.status,
        "stage": job.stage,
        "message": job.message,
        "result": job.result,
        "error": job.error,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
