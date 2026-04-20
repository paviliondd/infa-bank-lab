from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import time
import random
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

app = FastAPI(title="Bank Portal API")

# Prometheus Metrics
REQUEST_COUNT = Counter(
    'bank_requests_total', 'Tổng số HTTP requests nhận được',
    ['method', 'endpoint', 'http_status']
)
REQUEST_LATENCY = Histogram(
    'bank_request_latency_seconds', 'Độ trễ của các HTTP requests',
    ['method', 'endpoint']
)
TRANSFER_AMOUNT = Counter(
    'bank_transfer_amount_total', 'Tổng số tiền đã giao dịch thành công (USD)'
)

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    latency = time.time() - start_time
    
    # Chỉ track các API chính
    if request.url.path in ["/", "/transfer", "/api/balance"]:
        REQUEST_COUNT.labels(
            method=request.method, 
            endpoint=request.url.path, 
            http_status=response.status_code
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method, 
            endpoint=request.url.path
        ).observe(latency)
        
    return response

@app.get("/", response_class=HTMLResponse)
async def home():
    html_content = """
    <html>
        <head>
            <title>Bank Portal - LinuxUnity</title>
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; margin-top: 50px; background-color: #f4f7f6;}
                .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); display: inline-block;}
                h1 { color: #2c3e50; }
                p { color: #7f8c8d; font-size: 1.2em;}
                .btn { display: inline-block; padding: 10px 20px; margin-top: 20px; background-color: #3498db; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;}
                .btn:hover { background-color: #2980b9; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🏦 Xin chào đến với Bank Portal</h1>
                <p>Hệ thống Core Banking mô phỏng cho đồ án Capstone Lab 5.1</p>
                <a href="/docs" class="btn">Mở API Swagger</a>
            </div>
        </body>
    </html>
    """
    return html_content

@app.get("/api/balance")
async def get_balance():
    # Giả lập delay từ DB
    time.sleep(random.uniform(0.05, 0.2))
    return {"status": "success", "balance": 50000.0, "currency": "USD"}

@app.post("/transfer")
async def process_transfer(amount: float = 100.0):
    # Giả lập xử lý giao dịch phức tạp tốn CPU
    processing_time = random.uniform(0.1, 0.5)
    time.sleep(processing_time)
    
    if amount <= 0:
        return {"status": "error", "message": "Số tiền không hợp lệ"}
        
    # Ghi nhận metric tiền giao dịch
    TRANSFER_AMOUNT.inc(amount)
    return {
        "status": "success", 
        "message": f"Chuyển thành công ${amount}", 
        "tx_id": random.randint(100000, 999999)
    }

@app.get("/metrics")
async def metrics():
    # Expose metrics cho Prometheus scrape
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
