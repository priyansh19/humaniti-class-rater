"""Modal deployment of the worker API.

Deploy (needs `modal token new` or MODAL_TOKEN_ID/MODAL_TOKEN_SECRET, and organiser approval of the host - SPEC Q1):
    modal secret create rater-secrets RATER_ALLOWED_ORIGINS=https://<web>.vercel.app GEMINI_API_KEY=... RATER_API_KEY=...
    modal deploy modal_app.py
"""
import modal

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install_from_requirements("requirements.txt")
    .env({"RATER_ASR_MODEL": "base", "RATER_DATA_DIR": "/data", "HF_HUB_DISABLE_TELEMETRY": "1"})
    .run_commands("python -c \"from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')\"")
    .add_local_python_source("rater")
)
volume = modal.Volume.from_name("rater-data", create_if_missing=True)
app = modal.App("humaniti-class-rater-worker", image=image)


@app.function(
    cpu=4.0,
    memory=6144,
    volumes={"/data": volume},
    secrets=[modal.Secret.from_name("rater-secrets")],
    timeout=3 * 60 * 60,          # long uploads + 90-min recordings
    scaledown_window=20 * 60,     # keep warm while a job runs and the browser polls
    max_containers=1,             # single container: in-process queue + SQLite job store stay consistent
)
@modal.concurrent(max_inputs=64)
@modal.asgi_app()
def web():
    from rater.api.app import app as fastapi_app
    return fastapi_app
