# Worker image for Render / Railway / any Docker host (Modal uses modal_app.py instead).
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
ARG RATER_ASR_MODEL=base
ENV RATER_ASR_MODEL=${RATER_ASR_MODEL} HF_HUB_DISABLE_TELEMETRY=1
RUN python -c "import os; from faster_whisper import WhisperModel; WhisperModel(os.environ['RATER_ASR_MODEL'], device='cpu', compute_type='int8')"
COPY rater ./rater
ENV RATER_DATA_DIR=/data PORT=8000
RUN mkdir -p /data
EXPOSE 8000
CMD ["sh", "-c", "uvicorn rater.api.app:app --host 0.0.0.0 --port ${PORT} --workers 1 --timeout-keep-alive 75"]
