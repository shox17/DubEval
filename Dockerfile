# DubEval: the web interface (default) or the REST API, CPU only.
#   docker build -t dubeval .
#   docker run -p 127.0.0.1:8501:8501 -v dubeval-data:/data --env-file .env dubeval       # web: open the printed link
#   docker run --rm -v dubeval-data:/data --env-file .env dubeval python qa.py "<link>"    # CLI (files in /data/output)
#   docker run -p 8000:8000 -v dubeval-data:/data -e DUBEVAL_API_TOKEN=... dubeval \
#              python qa.py serve --host 0.0.0.0                                                  # API
FROM python:3.14-slim

# OpenCV and MediaPipe need GL/EGL and GLib; MediaPipe 1.x also imports sounddevice (PortAudio);
# ffmpeg comes with imageio-ffmpeg.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgl1 libegl1 libgles2 libglib2.0-0 libportaudio2 \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DUBEVAL_DATA=/data DUBEVAL_OUT=/data/output \
    XDG_CACHE_HOME=/home/app/.cache DUBEVAL_MODELS=/home/app/.cache/dubeval

# /data must exist and belong to the app user before VOLUME, or new volumes are created root-owned and unwritable.
RUN useradd --create-home --uid 1000 app && mkdir -p /data /app && chown app:app /data /app
WORKDIR /app

# requirements.txt is the runtime without PyTorch (speech on CTranslate2, the meaning screen on onnxruntime).
COPY requirements.txt .
# The pins were verified on Windows (Python 3.14). If one has no wheel for this image's platform, the MediaPipe pin is
# relaxed, as it is the package most often missing a wheel. (Not yet rebuilt and tested after the move to 3.14.)
RUN pip install -r requirements.txt \
 || (sed 's/^mediapipe==[^ ]*/mediapipe/' requirements.txt > /tmp/requirements.txt && pip install -r /tmp/requirements.txt)

COPY --chown=app:app . .
USER app

# Models baked in so the container works offline: the faster-whisper base model (~145 MB) and the speaker model
# (26 MB, SHA-256 checked).
RUN DUBEVAL_DEVICE=cpu python -c "from dubeval import asr; asr.load_model('base')" \
 && python -c "from dubeval import speaker; speaker.model_path()"

VOLUME /data
EXPOSE 8501 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD python -c "import urllib.request,sys; [urllib.request.urlopen(u, timeout=3) for u in sys.argv[1:2]]" \
      "http://127.0.0.1:8501/static/style.css" || exit 1
CMD ["dubeval", "web", "--host", "0.0.0.0", "--port", "8501", "--no-browser"]
