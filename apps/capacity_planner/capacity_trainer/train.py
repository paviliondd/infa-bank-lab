"""
Lab 4.2: Capacity Planning with Prophet (Trainer Job)
Thu thập CPU/Memory usage 30 ngày qua, dùng Prophet dự báo 30 ngày tới.
Xuất kết quả (.json) để Grafana Datasource đọc.
"""
import os
import json
import requests
import pandas as pd
from prophet import Prophet
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
            "step": "1h"  # Data point mỗi giờ
        },
        timeout=30
    )
    if response.status_code != 200:
        raise Exception(f"Prometheus API error: {response.text}")
        
    data = response.json()["data"]["result"]
    if not data:
        raise Exception("Không có metric nào được trả về (Empty DataFrame).")
        
    # Flatten metrics
    records = []
    for series in data:
        for val in series["values"]:
            records.append({
                "ds": datetime.fromtimestamp(val[0]), # Required format for prophet
                "y": float(val[1])
            })
            
    df = pd.DataFrame(records)
    # Trung bình theo giờ nếu có nhiều node
    df = df.groupby(df['ds'].dt.floor('H')).agg({'y': 'mean'}).reset_index()
    return df

def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    try:
        # 1. Thu thập dữ liệu
        df = fetch_prometheus_data(QUERY_CPU)
        print(f"Collected {len(df)} datapoints for Training.")
        
        # 2. Xây dựng model
        model = Prophet(yearly_seasonality=False, weekly_seasonality=True, daily_seasonality=True)
        model.fit(df)
        
        # 3. Dự đoán 30 ngày tương lai
        future = model.make_future_dataframe(periods=30*24, freq='H') # 30 ngày x 24h
        forecast = model.predict(future)
        
        # 4. Lưu Forecast để FastAPI/Grafana sử dụng
        # Grafana JSON Datasource cần array object: [{ time: ms, value: val }]
        forecast_export = []
        for _, row in forecast.tail(30*24).iterrows():
            forecast_export.append({
                "time": int(row['ds'].timestamp() * 1000),
                "value": round(row['yhat'], 2),
                "upper": round(row['yhat_upper'], 2),
                "lower": round(row['yhat_lower'], 2)
            })
            
        forecast_file = os.path.join(MODEL_DIR, "forecast_cpu.json")
        with open(forecast_file, 'w') as f:
            json.dump(forecast_export, f)
            
        # 5. Phân tích Breach Alert (Mức nguy hiểm > 90%)
        breach_report = {"breached_in_days": -1, "status": "SAFE"}
        for idx, row in forecast.tail(30*24).iterrows():
            if row['yhat_upper'] >= 90:
                delta = row['ds'] - datetime.utcnow()
                days = max(1, delta.days)
                breach_report = {"breached_in_days": days, "status": "DANGER", "date": str(row['ds'])}
                break
                
        breach_file = os.path.join(MODEL_DIR, "breach_report.json")
        with open(breach_file, 'w') as f:
            json.dump(breach_report, f)
            
        print("Training successfully finished! Files saved to NFS.")
        
    except Exception as e:
        print(f"[ERROR] Training failed: {e}")

if __name__ == "__main__":
    main()
