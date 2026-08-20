import threading
import uuid
from dataclasses import dataclass


@dataclass
class Job:
    status: str = "running"  # running | done | error
    stage: str = "starting"
    message: str = "Starting..."
    result: dict | None = None
    error: str | None = None


_jobs: dict[str, Job] = {}
_lock = threading.Lock()


def create_job() -> str:
    job_id = uuid.uuid4().hex
    with _lock:
        _jobs[job_id] = Job()
    return job_id


def update_job(job_id: str, stage: str, message: str) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job is not None:
            job.stage = stage
            job.message = message


def complete_job(job_id: str, result: dict) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job is not None:
            job.status = "done"
            job.result = result


def fail_job(job_id: str, error: str) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job is not None:
            job.status = "error"
            job.error = error


def get_job(job_id: str) -> Job | None:
    with _lock:
        return _jobs.get(job_id)
