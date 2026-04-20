"""
Lab 4.2: Capacity Planning Trainer (scikit-learn Linear Regression)
Thu thập CPU usage, dự báo 30 ngày tương lai bằng Linear Regression.
Xuất kết quả JSON để capacity-service đọc và expose lên Grafana.
"""
import os
import json
import requests
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://bank-monitoring-kube-prome-prometheus.monitoring.svc.cluster.local:9090")
MODEL_DIR = os.getenv("MODEL_DIR", "/model/capacity")
QUERY_CPU = '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'

def fetch_prometheus_data(query, days=30):
    print(f"Fetching data from Prometheus: {PROMETHEUS_URL}")
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)

    response = requests.get(
        f"{PROMETHEUS_URL}/api/v1/query_range",
        params={
            "query": query,
            "start": start_time.timestamp(),
            "end": end_time.timestamp(),
            "step": "1h"
        },
        timeout=30
    )
    if response.status_code != 200:
        raise Exception(f"Prometheus API error: {response.text}")

    data = response.json()["data"]["result"]
    if not data:
        raise Exception("Không có metric nào được trả về.")

    records = []
    for series in data:
        for val in series["values"]:
            records.append({
                "ts": float(val[0]),
                "y": float(val[1])
            })

    df = pd.DataFrame(records)
    df = df.groupby(df['ts'].apply(lambda x: int(x // 3600) * 3600)).agg({'y': 'mean'}).reset_index()
    df.columns = ['ts', 'y']
    return df

def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    try:
        # 1. Thu thập dữ liệu
        df = fetch_prometheus_data(QUERY_CPU)
        print(f"Collected {len(df)} datapoints for Training.")

        if len(df) < 5:
            raise Exception(f"Không đủ dữ liệu để train (cần ít nhất 5, có {len(df)}).")

        # 2. Train Linear Regression
        X = df['ts'].values.reshape(-1, 1)
        y = df['y'].values
        model = LinearRegression()
        model.fit(X, y)

        # 3. Tạo timestamps cho 30 ngày tương lai
        last_ts = df['ts'].max()
        future_timestamps = [last_ts + i * 3600 for i in range(1, 30 * 24 + 1)]
        X_future = np.array(future_timestamps).reshape(-1, 1)
        predictions = model.predict(X_future)

        # Tính confidence band ±5%
        residuals = y - model.predict(X)
        std = np.std(residuals)

        # 4. Xuất forecast JSON
        forecast_export = []
        for ts, pred in zip(future_timestamps, predictions):
            forecast_export.append({
                "time": int(ts * 1000),  # milliseconds cho Grafana
                "value": round(float(np.clip(pred, 0, 100)), 2),
                "upper": round(float(np.clip(pred + 2 * std, 0, 100)), 2),
                "lower": round(float(np.clip(pred - 2 * std, 0, 100)), 2)
            })

        with open(os.path.join(MODEL_DIR, "forecast_cpu.json"), 'w') as f:
            json.dump(forecast_export, f)

        # 5. Phân tích Breach Alert (CPU > 90%)
        breach_report = {"breached_in_days": -1, "status": "SAFE"}
        now = datetime.utcnow().timestamp()
        for entry in forecast_export:
            ts_sec = entry["time"] / 1000
            if entry["upper"] >= 90:
                days_left = max(1, int((ts_sec - now) / 86400))
                breach_report = {
                    "breached_in_days": days_left,
                    "status": "DANGER",
                    "date": datetime.utcfromtimestamp(ts_sec).isoformat()
                }
                break

        with open(os.path.join(MODEL_DIR, "breach_report.json"), 'w') as f:
            json.dump(breach_report, f)

        print(f"Training successful! Breach report: {breach_report}")
        print("Files saved to NFS.")

    except Exception as e:
        print(f"[ERROR] Training failed: {e}")
        raise

if __name__ == "__main__":
    main()
