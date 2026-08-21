import requests

URL = "http://127.0.0.1:8000/api/v1/logs"
SEARCH_URL = "http://127.0.0.1:8000/api/v1/search"
ANALYZE_URL = "http://127.0.0.1:8000/api/v1/analyze"

HEADERS = {
    "x-api-key": "super-secret-key-123",
    "Content-Type": "application/json"
}

# 1. Ingest sample error logs
sample_errors = [
    {"service_name": "auth-service", "endpoint": "/login", "response_time_ms": 120.0, "status_code": 500, "error_message": "ConnectionRefusedError: Database pool exhausted on port 5432"},
    {"service_name": "payment-service", "endpoint": "/checkout", "response_time_ms": 450.0, "status_code": 502, "error_message": "Stripe API gateway timeout after 30000ms"},
    {"service_name": "user-service", "endpoint": "/profile", "response_time_ms": 80.0, "status_code": 401, "error_message": "JWT TokenExpiredError: Signature verification failed"}
]

print("--- 1. Indexing Error Logs ---")
for payload in sample_errors:
    res = requests.post(URL, json=payload, headers=HEADERS)
    print(f"Indexed [{payload['service_name']}]:", res.json().get("log_id"))

# 2. Perform a semantic vector query
print("\n--- 2. Testing Vector RAG Search ---")
query = "database connection failure"
search_res = requests.get(SEARCH_URL, params={"query": query}, headers=HEADERS)
print(f"Query: '{query}'")
print("Vector Matches:", search_res.json())

# 3. Test AI Root Cause Analysis Endpoint
print("\n--- 3. Testing Root Cause Analysis ---")
analyze_res = requests.get(ANALYZE_URL, params={"query": query}, headers=HEADERS)
print("Analysis Response:")
print(analyze_res.json().get("root_cause_analysis"))