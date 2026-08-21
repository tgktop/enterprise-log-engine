import os
import uuid
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel, Field
from typing import Optional
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from analytics import AnomalyEngine
from rag_engine import LogVectorEngine
from database import get_db, LogModel

load_dotenv()

API_SECRET_KEY = os.getenv("API_SECRET_KEY", "super-secret-key-123")

app = FastAPI(
    title="Enterprise Log Intelligence Engine",
    version="1.0.0",
    description="Asynchronous ingestion, statistical anomaly detection, & vector RAG engine."
)

detector = AnomalyEngine(z_threshold=2.0)
vector_db = LogVectorEngine()

class LogPayload(BaseModel):
    service_name: str = Field(..., example="auth-service")
    endpoint: str = Field(..., example="/api/v1/login")
    response_time_ms: float = Field(..., gt=0, example=245.5)
    status_code: int = Field(..., ge=100, le=599, example=500)
    error_message: Optional[str] = Field(None, example="Database connection timeout")

async def verify_api_token(x_api_key: str = Header(...)):
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key credentials")
    return x_api_key

@app.get("/")
async def health_check():
    return {"status": "online", "system": "Enterprise Log Engine"}

@app.post("/api/v1/logs", dependencies=[Depends(verify_api_token)])
async def ingest_log(payload: LogPayload, db: Session = Depends(get_db)):
    log_id = str(uuid.uuid4())
    analysis = detector.evaluate_latency(payload.response_time_ms)
    
    db_log = LogModel(
        id=log_id,
        service_name=payload.service_name,
        endpoint=payload.endpoint,
        response_time_ms=payload.response_time_ms,
        status_code=payload.status_code,
        error_message=payload.error_message
    )
    db.add(db_log)
    db.commit()

    if payload.error_message:
        vector_db.index_error_log(
            log_id=log_id,
            error_message=payload.error_message,
            service_name=payload.service_name
        )

    return {
        "log_id": log_id,
        "status": "accepted",
        "service": payload.service_name,
        "metrics": {"response_time": payload.response_time_ms, "status_code": payload.status_code},
        "anomaly_analysis": analysis
    }

@app.get("/api/v1/search", dependencies=[Depends(verify_api_token)])
async def search_logs(query: str):
    matches = vector_db.query_similar_errors(query)
    return {"query": query, "matches": matches}

@app.get("/api/v1/analyze", dependencies=[Depends(verify_api_token)])
async def analyze_incident(query: str):
    analysis = vector_db.generate_root_cause_analysis(query)
    return {"query": query, "root_cause_analysis": analysis}