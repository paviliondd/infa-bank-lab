"""
Lab 4.1 — AIOps: FastAPI Anomaly Detection Service
====================================================
Service chính cung cấp 3 endpoints:
  GET  /health     → Health check
  POST /predict    → Nhận metric vector, trả về anomaly score (on-demand)
  GET  /metrics    → Prometheus scrape endpoint (custom exporter format)

Khởi động:
  uvicorn main:app --host 0.0.0.0 --port 8000

Environment Variables:
  PROMETHEUS_URL      : Prometheus HTTP API URL
  MODEL_PATH          : Đường dẫn anomaly_model.pkl
  SCALER_PATH         : Đường dẫn scaler.pkl
  THRESHOLD_PATH      : Đường dẫn threshold.txt
  COLLECT_INTERVAL_SEC: Interval thu thập metrics (giây, mặc định 60)
  LOG_LEVEL           : Logging level (INFO / DEBUG)
"""

import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    generate_latest,
)
from pydantic import BaseModel, Field

from collector import MetricsCollector

# ───────────────── Logging Setup ──────────────────────────────────────── #

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("aiops.main")


# ───────────────── Config Paths ───────────────────────────────────────── #

MODEL_PATH     = os.getenv("MODEL_PATH",     "/model/anomaly_model.pkl")
SCALER_PATH    = os.getenv("SCALER_PATH",    "/model/scaler.pkl")
THRESHOLD_PATH = os.getenv("THRESHOLD_PATH", "/model/threshold.txt")
INFO_PATH      = os.getenv("INFO_PATH",      "/model/model_info.json")


# ───────────────── Prometheus Metrics (Custom Exporter) ───────────────── #

AIOPS_ANOMALY_DETECTED = Gauge(
    "aiops_anomaly_detected",
    "1 nếu phát hiện anomaly trong lần thu thập gần nhất, 0 nếu bình thường",
)
AIOPS_ANOMALY_SCORE = Gauge(
    "aiops_anomaly_score",
    "Điểm bất thường của Isolation Forest (âm = bất thường hơn)",
)
AIOPS_CPU_USAGE = Gauge(
    "aiops_observed_cpu_usage_percent",
    "CPU usage (%) đang quan sát bởi AIOps service",
)
AIOPS_MEMORY_USAGE = Gauge(
    "aiops_observed_memory_usage_percent",
    "Memory usage (%) đang quan sát bởi AIOps service",
)
AIOPS_NETWORK_BYTES = Gauge(
    "aiops_observed_network_receive_bytes_per_sec",
    "Network receive rate (bytes/s) đang quan sát",
)
AIOPS_COLLECTIONS_TOTAL = Counter(
    "aiops_collections_total",
    "Tổng số lần thu thập metrics thành công",
)
AIOPS_ANOMALY_TOTAL = Counter(
    "aiops_anomaly_total",
    "Tổng số lần phát hiện anomaly kể từ khi service khởi động",
)
AIOPS_COLLECTION_ERRORS = Counter(
    "aiops_collection_errors_total",
    "Tổng số lần thu thập metrics thất bại",
)
AIOPS_MODEL_LOADED = Gauge(
    "aiops_model_loaded",
    "1 nếu model đang được load thành công, 0 nếu chưa",
)

_GAUGES = {
    "anomaly_detected":   AIOPS_ANOMALY_DETECTED,
    "anomaly_score":      AIOPS_ANOMALY_SCORE,
    "cpu_usage":          AIOPS_CPU_USAGE,
    "memory_usage":       AIOPS_MEMORY_USAGE,
    "network_bytes":      AIOPS_NETWORK_BYTES,
    "collections_total":  AIOPS_COLLECTIONS_TOTAL,
    "anomaly_total":      AIOPS_ANOMALY_TOTAL,
    "collection_errors":  AIOPS_COLLECTION_ERRORS,
}


# ───────────────── Model State ────────────────────────────────────────── #

_model     = None
_scaler    = None
_threshold = None
_model_info: dict = {}


def load_model():
    """Load model artifacts từ PVC. Trả về True nếu thành công."""
    global _model, _scaler, _threshold, _model_info

    if not os.path.exists(MODEL_PATH):
        logger.warning(f"Model chưa tồn tại: {MODEL_PATH} — Chờ training job chạy...")
        AIOPS_MODEL_LOADED.set(0)
        return False

    try:
        _model     = joblib.load(MODEL_PATH)
        _scaler    = joblib.load(SCALER_PATH)
        with open(THRESHOLD_PATH) as f:
            _threshold = float(f.read().strip())
        if os.path.exists(INFO_PATH):
            with open(INFO_PATH) as f:
                _model_info = json.load(f)

        AIOPS_MODEL_LOADED.set(1)
        logger.info(f"Model loaded OK | threshold={_threshold:.6f} | trained_at={_model_info.get('trained_at','?')}")
        return True
    except Exception as e:
        logger.error(f"Load model thất bại: {e}", exc_info=True)
        AIOPS_MODEL_LOADED.set(0)
        return False


def get_model_data():
    """Trả về (model, scaler, threshold) hoặc None nếu chưa load."""
    if _model is None or _scaler is None or _threshold is None:
        # Thử load lại (trường hợp training job vừa hoàn thành)
        load_model()
    if _model is None:
        return None
    return _model, _scaler, _threshold


# ───────────────── FastAPI App ────────────────────────────────────────── #

_collector: Optional[MetricsCollector] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / Shutdown lifecycle."""
    global _collector

    logger.info("=" * 50)
    logger.info("  AIOps Anomaly Detection Service — Lab 4.1")
    logger.info("=" * 50)

    # Load model
    load_model()

    # Khởi động background collector
    _collector = MetricsCollector(model_loader_fn=get_model_data, gauges=_GAUGES)
    _collector.start()
    logger.info("Background collector đã khởi động")

    yield  # App running

    # Shutdown
    if _collector:
        _collector.stop()
        _collector.join(timeout=5)
    logger.info("Service đã dừng lại sạch sẽ")


app = FastAPI(
    title="AIOps Anomaly Detection Service",
    description="Lab 4.1 — Phát hiện bất thường hạ tầng Banking bằng Isolation Forest",
    version="1.0.0",
    lifespan=lifespan,
)


# ───────────────── Request / Response Models ──────────────────────────── #

class PredictRequest(BaseModel):
    cpu_usage_percent: float = Field(
        ..., ge=0, le=100,
        description="CPU usage (%)",
        example=45.2
    )
    memory_usage_percent: float = Field(
        ..., ge=0, le=100,
        description="Memory usage (%)",
        example=62.8
    )
    network_receive_bytes_per_sec: float = Field(
        ..., ge=0,
        description="Network receive rate (bytes/s)",
        example=1_500_000
    )


class PredictResponse(BaseModel):
    is_anomaly: bool
    anomaly_score: float
    threshold: float
    message: str
    input_metrics: dict


# ───────────────── Endpoints ──────────────────────────────────────────── #

@app.get("/health", summary="Health Check")
def health():
    """Service health check."""
    model_ok = _model is not None
    last_metrics = _collector.get_last_metrics() if _collector else None
    return {
        "status":        "healthy" if model_ok else "degraded",
        "model_loaded":  model_ok,
        "model_info":    _model_info,
        "last_metrics":  last_metrics,
        "threshold":     _threshold,
        "uptime_seconds": time.time(),
    }


@app.post("/predict", response_model=PredictResponse, summary="On-demand Anomaly Prediction")
def predict(req: PredictRequest):
    """
    Nhận metric vector, trả về anomaly score và kết quả phân loại.
    Endpoint này dùng để test thủ công hoặc tích hợp với external tools.
    """
    model_data = get_model_data()
    if model_data is None:
        raise HTTPException(
            status_code=503,
            detail="Model chưa sẵn sàng. Training job chưa chạy xong."
        )

    model, scaler, threshold = model_data

    X_raw = [[
        req.cpu_usage_percent,
        req.memory_usage_percent,
        req.network_receive_bytes_per_sec,
    ]]
    X_scaled    = scaler.transform(X_raw)
    score       = float(model.decision_function(X_scaled)[0])
    is_anomaly  = score < threshold

    return PredictResponse(
        is_anomaly    = is_anomaly,
        anomaly_score = round(score, 6),
        threshold     = round(threshold, 6),
        message       = "🔴 ANOMALY DETECTED" if is_anomaly else "🟢 Normal traffic",
        input_metrics = {
            "cpu_usage_percent":             req.cpu_usage_percent,
            "memory_usage_percent":          req.memory_usage_percent,
            "network_receive_bytes_per_sec": req.network_receive_bytes_per_sec,
        },
    )


@app.get("/metrics", response_class=PlainTextResponse, summary="Prometheus Metrics Endpoint")
def metrics():
    """
    Prometheus scrape endpoint.
    Trả về toàn bộ metrics theo định dạng Prometheus text format.
    """
    return PlainTextResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/", summary="Service Info")
def root():
    return {
        "service":  "AIOps Anomaly Detection — Lab 4.1",
        "version":  "1.0.0",
        "endpoints": {
            "health":  "/health",
            "predict": "/predict  [POST]",
            "metrics": "/metrics  [GET, Prometheus scrape]",
            "docs":    "/docs",
        },
    }
