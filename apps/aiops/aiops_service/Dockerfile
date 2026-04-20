# ─────────────────────────────────────────────────────────────────────── #
#  AIOps Service — Dockerfile
#  Build: docker build -t aiops-service:latest .
#  Run:   docker run -p 8000:8000 -v /opt/model:/model aiops-service
# ─────────────────────────────────────────────────────────────────────── #

FROM python:3.11-slim AS base

# Cài đặt deps hệ thống (libgomp cần cho scikit-learn parallel)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Install Python dependencies ──────────────────────────────────────── #
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Copy source code ─────────────────────────────────────────────────── #
COPY main.py collector.py ./

# ── Non-root user (bảo mật) ──────────────────────────────────────────── #
RUN useradd --no-create-home --shell /bin/false aiops
USER aiops

# Model directory sẽ được mount từ NFS PVC
VOLUME ["/model"]

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]
