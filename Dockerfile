FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    COQUI_TOS_AGREED=1 \
    HF_HOME=/root/.cache/huggingface \
    TTS_HOME=/root/.local/share/tts

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        git \
        build-essential \
        libsndfile1 \
        libsndfile1-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install CUDA-enabled torch + torchaudio FIRST. Pinned to 2.7.x with cu128 to
# support Blackwell (RTX 5090, sm_120). torchcodec is required by torchaudio's
# load_with_torchcodec() in newer versions.
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cu128 \
        torch==2.7.0 torchaudio==2.7.0 \
 && pip install --no-cache-dir torchcodec \
 && pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir \
        "transformers>=4.33.0,<4.41.0" \
        "tokenizers>=0.13.3,<0.20" \
        "huggingface_hub<0.26"

COPY . .

# Shim that patches torch.load to weights_only=False (required for XTTS v2 with torch>=2.6)
# and then execs server.py.
RUN printf '%s\n' \
    'import torch as _t' \
    '_orig_load = _t.load' \
    'def _patched_load(*a, **kw):' \
    '    kw.setdefault("weights_only", False)' \
    '    return _orig_load(*a, **kw)' \
    '_t.load = _patched_load' \
    'import runpy, sys' \
    'sys.argv = ["server.py"] + sys.argv[1:]' \
    'runpy.run_path("server.py", run_name="__main__")' \
    > /app/_entrypoint.py

EXPOSE 5123

CMD ["python", "/app/_entrypoint.py", "--host", "0.0.0.0", "--port", "5123"]
