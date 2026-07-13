# Frozen environment for exact reproduction of the literature-search pipeline.
# Pin the digest for full reproducibility, e.g.:
#   FROM python:3.11-slim@sha256:<digest>
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt

COPY . .
RUN pip install --no-cache-dir -e .

# Default: re-run the frozen search reproduction from committed raw payloads.
CMD ["python", "-m", "quantum_diffusion_search", "reproduce", \
     "--raw-run", "data/raw/2026-07-09T184559Z_780688a"]
