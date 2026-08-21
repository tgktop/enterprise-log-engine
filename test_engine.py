import time
import requests

URL = "http://127.0.0.1:8000/api/v1/logs"
HEADERS = {
    "x-api-key": "super-secret-key-123",
    "Content-Type": "application/json"
}

# 1. Send normal baseline traffic (~200ms latency)
print("--- Sending Baseline Traffic ---")
for i in range(6):
    payload = {
        "service_name": "auth-service",
        "endpoint": "/api/v1/login",
        "response_time_ms": 200.0 + (i * 2),
        "status_code": 200,
        "error_message": None
    }
    response = requests.post(URL, json=payload, headers=HEADERS)
    print(f"Request {i+1}:", response.json())
    time.sleep(0.5)

# 2. Trigger an Anomaly Spike (1500ms latency)
print("\n--- Injecting Latency Anomaly ---")
anomaly_payload = {
    "service_name": "auth-service",
    "endpoint": "/api/v1/login",
    "response_time_ms": 1500.0,
    "status_code": 504,
    "error_message": "Gateway Timeout"
}
response = requests.post(URL, json=anomaly_payload, headers=HEADERS)
print("Anomaly Request:", response.json())