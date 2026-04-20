"""
Lab 4.1 — AIOps: Background Prometheus Metrics Collector
=========================================================
Module này chạy trong background thread, cứ mỗi COLLECT_INTERVAL giây
sẽ pull metrics mới nhất từ Prometheus, chạy qua Isolation Forest model,
và cập nhật Prometheus Gauge (dùng cho /metrics endpoint).
"""

import logging
import os
import threading
import time
from typing import Optional

import requests

logger = logging.getLogger("aiops.collector")

# ─────────────── Config từ Environment Variables ─────────────────────── #

PROMETHEUS_URL     = os.getenv(
    "PROMETHEUS_URL",
    "http://bank-monitoring-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090"
)
COLLECT_INTERVAL   = int(os.getenv("COLLECT_INTERVAL_SEC", "60"))   # giây
PROMETHEUS_TIMEOUT = int(os.getenv("PROMETHEUS_TIMEOUT",   "10"))


# ─────────────── Prometheus instant query helper ─────────────────────── #

def _instant_query(promql: str) -> Optional[float]:
    """
    Gọi Prometheus /api/v1/query (instant), trả về float hoặc None nếu lỗi.
    Lấy trung bình của tất cả series nếu có nhiều kết quả.
    """
    url = f"{PROMETHEUS_URL}/api/v1/query"
    try:
        resp = requests.get(
            url,
            params={"query": promql},
            timeout=PROMETHEUS_TIMEOUT
        )
        resp.raise_for_status()
        results = resp.json().get("data", {}).get("result", [])
        if not results:
            return None
        values = [float(r["value"][1]) for r in results if r.get("value")]
        return float(sum(values) / len(values)) if values else None
    except Exception as e:
        logger.warning(f"Prometheus query lỗi ({promql[:50]}...): {e}")
        return None


def fetch_current_metrics() -> Optional[dict]:
    """
    Lấy metrics hiện tại từ Prometheus.
    Trả về dict hoặc None nếu không lấy được.
    """
    cpu = _instant_query(
        '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
    )
    memory = _instant_query(
        '100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))'
    )
    network = _instant_query(
        'sum(rate(node_network_receive_bytes_total{device!="lo"}[5m]))'
    )

    if any(v is None for v in [cpu, memory, network]):
        logger.warning("Không lấy được đủ metrics từ Prometheus")
        return None

    # Clip giá trị hợp lệ
    cpu     = max(0.0, min(100.0, cpu))
    memory  = max(0.0, min(100.0, memory))
    network = max(0.0, network)

    return {
        "cpu_usage_percent":             cpu,
        "memory_usage_percent":          memory,
        "network_receive_bytes_per_sec": network,
    }


# ─────────────────────── Background Collector ─────────────────────────── #

class MetricsCollector(threading.Thread):
    """
    Background thread thu thập metrics và cập nhật anomaly score.
    """

    def __init__(self, model_loader_fn, gauges: dict):
        """
        Args:
            model_loader_fn : Callable trả về (model, scaler, threshold)
            gauges          : Dict chứa prometheus_client Gauge objects
        """
        super().__init__(daemon=True, name="AIOpsCollector")
        self._get_model    = model_loader_fn
        self._gauges       = gauges
        self._stop_event   = threading.Event()
        self._last_metrics: Optional[dict] = None
        self._last_score:   Optional[float] = None
        self._error_count   = 0
        self._collect_count = 0

    def stop(self):
        self._stop_event.set()

    def get_last_metrics(self) -> Optional[dict]:
        return self._last_metrics

    def get_last_score(self) -> Optional[float]:
        return self._last_score

    def run(self):
        logger.info(f"Collector bắt đầu (interval={COLLECT_INTERVAL}s, prometheus={PROMETHEUS_URL})")

        # Chờ 5 giây cho model load xong trước khi bắt đầu collect
        time.sleep(5)

        while not self._stop_event.is_set():
            start = time.monotonic()
            try:
                self._collect_once()
            except Exception as e:
                self._error_count += 1
                logger.error(f"Collect cycle lỗi: {e}", exc_info=True)

            elapsed = time.monotonic() - start
            sleep_time = max(0, COLLECT_INTERVAL - elapsed)
            self._stop_event.wait(timeout=sleep_time)

    def _collect_once(self):
        metrics = fetch_current_metrics()
        if metrics is None:
            self._error_count += 1
            # Cập nhật gauge lỗi
            self._gauges["collection_errors"].inc()
            return

        self._last_metrics   = metrics
        self._collect_count += 1

        # Cập nhật raw metrics gauges
        self._gauges["cpu_usage"].set(metrics["cpu_usage_percent"])
        self._gauges["memory_usage"].set(metrics["memory_usage_percent"])
        self._gauges["network_bytes"].set(metrics["network_receive_bytes_per_sec"])

        # Lấy model và tính anomaly score
        model_data = self._get_model()
        if model_data is None:
            logger.warning("Model chưa sẵn sàng, bỏ qua cycle này")
            return

        model, scaler, threshold = model_data

        # Chuẩn bị input vector
        X_raw = [[
            metrics["cpu_usage_percent"],
            metrics["memory_usage_percent"],
            metrics["network_receive_bytes_per_sec"],
        ]]
        X_scaled = scaler.transform(X_raw)

        # Tính anomaly score
        score      = float(model.decision_function(X_scaled)[0])
        is_anomaly = int(score < threshold)

        self._last_score = score

        # Cập nhật anomaly gauges
        self._gauges["anomaly_score"].set(score)
        self._gauges["anomaly_detected"].set(is_anomaly)

        if is_anomaly:
            self._gauges["anomaly_total"].inc()
            logger.warning(
                f"[ANOMALY DETECTED] score={score:.4f} threshold={threshold:.4f} | "
                f"cpu={metrics['cpu_usage_percent']:.1f}% | "
                f"mem={metrics['memory_usage_percent']:.1f}% | "
                f"net={metrics['network_receive_bytes_per_sec']:.0f} bytes/s"
            )
        else:
            logger.debug(
                f"[Normal] score={score:.4f} | "
                f"cpu={metrics['cpu_usage_percent']:.1f}% | "
                f"mem={metrics['memory_usage_percent']:.1f}%"
            )

        self._gauges["collections_total"].inc()
