#!/usr/bin/env python3
"""
Lab 4.1 — AIOps: Thu thập Metrics từ Prometheus HTTP API
=========================================================
Script này pull dữ liệu lịch sử từ Prometheus trong khoảng thời gian
đã chỉ định (mặc định 3 ngày) và xuất ra file CSV dùng để train model.

Metrics thu thập:
  - node_cpu_usage_percent       : CPU usage (%) của từng node
  - node_memory_usage_bytes      : Memory working set (bytes)
  - node_network_receive_bytes   : Network inbound (bytes/s)

Cách dùng:
  python prometheus_collector.py \
    --prometheus-url http://bank-monitoring-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090 \
    --days 3 \
    --output /model/metrics_dataset.csv
"""

import argparse
import sys
import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone


# ─────────────────────────── Config mặc định ───────────────────────────── #

DEFAULT_PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://bank-monitoring-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090"
)
DEFAULT_DAYS     = int(os.getenv("COLLECTION_DAYS", "3"))
DEFAULT_STEP     = os.getenv("COLLECTION_STEP", "5m")       # 5 phút/sample
DEFAULT_OUTPUT   = os.getenv("OUTPUT_PATH", "/model/metrics_dataset.csv")


# ────────────────────────── Helper functions ───────────────────────────── #

def query_range(prometheus_url: str, promql: str, start: datetime, end: datetime, step: str) -> pd.DataFrame:
    """
    Gọi Prometheus range query API, trả về DataFrame với cột [timestamp, value, instance].
    """
    url = f"{prometheus_url}/api/v1/query_range"
    params = {
        "query": promql,
        "start": start.timestamp(),
        "end":   end.timestamp(),
        "step":  step,
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Không kết nối được Prometheus: {prometheus_url}", file=sys.stderr)
        return pd.DataFrame()
    except requests.exceptions.HTTPError as e:
        print(f"[ERROR] Prometheus API lỗi: {e}", file=sys.stderr)
        return pd.DataFrame()

    data   = resp.json()
    result = data.get("data", {}).get("result", [])

    if not result:
        print(f"[WARN] Không có dữ liệu cho query: {promql}", file=sys.stderr)
        return pd.DataFrame()

    rows = []
    for series in result:
        instance = series.get("metric", {}).get("instance", series.get("metric", {}).get("node", "unknown"))
        for ts, val in series["values"]:
            rows.append({"timestamp": float(ts), "value": float(val), "instance": instance})

    return pd.DataFrame(rows)


def collect_cpu(prometheus_url: str, start: datetime, end: datetime, step: str) -> pd.DataFrame:
    """
    CPU usage % = 100 - idle%
    PromQL: avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100
    Đảo ngược: cpu_usage = 100 - idle_rate * 100
    """
    promql = (
        '100 - (avg by (instance) ('
        '  rate(node_cpu_seconds_total{mode="idle"}[5m])'
        ') * 100)'
    )
    df = query_range(prometheus_url, promql, start, end, step)
    if df.empty:
        return df
    df = df.rename(columns={"value": "cpu_usage_percent"})
    return df


def collect_memory(prometheus_url: str, start: datetime, end: datetime, step: str) -> pd.DataFrame:
    """
    Memory usage % = working_set / total * 100
    """
    promql = (
        '100 * ('
        '  1 - ('
        '    node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes'
        '  )'
        ')'
    )
    df = query_range(prometheus_url, promql, start, end, step)
    if df.empty:
        return df
    df = df.rename(columns={"value": "memory_usage_percent"})
    return df


def collect_network(prometheus_url: str, start: datetime, end: datetime, step: str) -> pd.DataFrame:
    """
    Network receive rate (bytes/s) — tổng tất cả interface của mỗi node
    """
    promql = (
        'sum by (instance) ('
        '  rate(node_network_receive_bytes_total{device!="lo"}[5m])'
        ')'
    )
    df = query_range(prometheus_url, promql, start, end, step)
    if df.empty:
        return df
    df = df.rename(columns={"value": "network_receive_bytes_per_sec"})
    return df


# ─────────────────────────────── Main ─────────────────────────────────── #

def main():
    parser = argparse.ArgumentParser(description="AIOps Prometheus Data Collector")
    parser.add_argument("--prometheus-url", default=DEFAULT_PROMETHEUS_URL)
    parser.add_argument("--days",           type=int,   default=DEFAULT_DAYS)
    parser.add_argument("--step",           default=DEFAULT_STEP)
    parser.add_argument("--output",         default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    end_time   = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=args.days)

    print(f"[INFO] Prometheus URL : {args.prometheus_url}")
    print(f"[INFO] Thu thập       : {args.days} ngày ({start_time.strftime('%Y-%m-%d')} → {end_time.strftime('%Y-%m-%d')})")
    print(f"[INFO] Step           : {args.step}")
    print(f"[INFO] Output         : {args.output}")

    # Thu thập 3 loại metrics
    print("\n[1/3] Thu thập CPU usage...")
    df_cpu = collect_cpu(args.prometheus_url, start_time, end_time, args.step)

    print("[2/3] Thu thập Memory usage...")
    df_mem = collect_memory(args.prometheus_url, start_time, end_time, args.step)

    print("[3/3] Thu thập Network receive rate...")
    df_net = collect_network(args.prometheus_url, start_time, end_time, args.step)

    # Validate
    if df_cpu.empty or df_mem.empty or df_net.empty:
        print("[ERROR] Một hoặc nhiều metric trống. Kiểm tra kết nối Prometheus.")
        sys.exit(1)

    # Merge theo timestamp + instance (aggregate trên node, lấy mean nếu có nhiều instance)
    df_cpu_agg = df_cpu.groupby("timestamp")["cpu_usage_percent"].mean().reset_index()
    df_mem_agg = df_mem.groupby("timestamp")["memory_usage_percent"].mean().reset_index()
    df_net_agg = df_net.groupby("timestamp")["network_receive_bytes_per_sec"].mean().reset_index()

    df = df_cpu_agg.merge(df_mem_agg, on="timestamp").merge(df_net_agg, on="timestamp")
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Clip giá trị bất hợp lệ
    df["cpu_usage_percent"]           = df["cpu_usage_percent"].clip(0, 100)
    df["memory_usage_percent"]        = df["memory_usage_percent"].clip(0, 100)
    df["network_receive_bytes_per_sec"] = df["network_receive_bytes_per_sec"].clip(0)

    # Loại bỏ NaN
    df = df.dropna()

    # Lưu file
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    df.to_csv(args.output, index=False)

    print(f"\n[✓] Thu thập thành công: {len(df)} samples")
    print(f"[✓] Saved: {args.output}")
    print(f"\nThống kê:\n{df[['cpu_usage_percent', 'memory_usage_percent', 'network_receive_bytes_per_sec']].describe()}")


if __name__ == "__main__":
    main()
