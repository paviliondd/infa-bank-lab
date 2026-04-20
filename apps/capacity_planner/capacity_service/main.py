"""
FastAPI Service acting as SimpleJSON Datasource for Grafana.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import PlainTextResponse

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

MODEL_DIR = os.getenv("MODEL_DIR", "/model/capacity")

# Prometheus Exporter for AlertManager
DAYS_UNTIL_BREACH = Gauge('capacity_days_until_breach', 'So ngay truoc khi CPU dat muc 90%. 999 = An toan.')

def load_data():
    forecast_file = os.path.join(MODEL_DIR, "forecast_cpu.json")
    breach_file = os.path.join(MODEL_DIR, "breach_report.json")
    
    forecasts = []
    if os.path.exists(forecast_file):
        try:
            with open(forecast_file) as f:
                forecasts = json.load(f)
        except Exception:
            pass
            
    if os.path.exists(breach_file):
        try:
            with open(breach_file) as f:
                breach = json.load(f)
                if breach.get('breached_in_days', -1) > 0:
                    DAYS_UNTIL_BREACH.set(breach['breached_in_days'])
                else:
                    DAYS_UNTIL_BREACH.set(999) # SAFE
        except Exception:
            pass
            
    return forecasts

@app.get("/")
def root():
    return {"status": "ok", "message": "JSON Datasource API"}

@app.post("/search")
async def search(request: Request):
    return ["cpu_forecast", "cpu_forecast_upper", "cpu_forecast_lower"]

@app.post("/query")
async def query(request: Request):
    req = await request.json()
    forecasts = load_data()
    if not forecasts:
        return []
        
    targets = req.get("targets", [])
    response = []
    
    for t in targets:
        target_name = t.get("target")
        datapoints = []
        for f in forecasts:
            if target_name == "cpu_forecast":
                datapoints.append([f["value"], f["time"]])
            elif target_name == "cpu_forecast_upper":
                datapoints.append([f["upper"], f["time"]])
            elif target_name == "cpu_forecast_lower":
                datapoints.append([f["lower"], f["time"]])
                
        if datapoints:
            response.append({
                "target": target_name,
                "datapoints": datapoints
            })
            
    return response

@app.post("/annotations")
async def annotations(request: Request):
    return []

@app.get("/metrics")
def metrics():
    load_data() # Update gauge
    return PlainTextResponse(content=generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST)
