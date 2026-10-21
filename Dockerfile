# Full app (MP4 upload/link + Whisper + frames). Works on Render / Railway / Modal / HF Docker Spaces.
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-full.txt .
RUN pip install --no-cache-dir -r requirements-full.txt
# Pre-fetch the Whisper model so the first request is not slowed by a download.
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"
COPY . .
ENV PORT=7860 GRADIO_SERVER_NAME=0.0.0.0 TMPDIR=/tmp
EXPOSE 7860
CMD ["python", "app.py"]
