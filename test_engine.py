import pytest
import pytest_asyncio
from rag_engine import LogVectorEngine

@pytest.fixture
def engine(tmp_path):
    db_dir = str(tmp_path / "test_chroma_db")
    return LogVectorEngine(db_path=db_dir, max_distance_threshold=0.75)

@pytest.mark.asyncio
async def test_async_query_with_metadata_filter(engine):
    engine.index_error_log("1", "Database timeout", "db-service", environment="production")
    engine.index_error_log("2", "Database timeout", "db-service", environment="staging")
    
    results = await engine.query_similar_errors_async(
        "Database timeout", 
        where_filter={"environment": "production"}
    )
    
    assert len(results["documents"][0]) == 1
    assert results["metadatas"][0][0]["environment"] == "production"

@pytest.mark.asyncio
async def test_distance_threshold_filtering(engine):
    engine.index_error_log("1", "User failed to upload avatar image", "user-service")
    results = await engine.query_similar_errors_async("Out of memory crash in payment service")
    assert results["documents"] == [[]]

def test_smart_truncation(engine):
    long_log = "START_ERROR " + ("x" * 2500) + " END_TRACEBACK"
    sanitized = engine.sanitize_log(long_log)
    
    assert "START_ERROR" in sanitized
    assert "END_TRACEBACK" in sanitized
    assert "[TRUNCATED STACKTRACE]" in sanitized
    assert len(sanitized) < 2000

@pytest.mark.asyncio
async def test_async_api_failure_fallback(engine):
    class MockFailedClient:
        class models:
            @staticmethod
            def generate_content(*args, **kwargs):
                raise RuntimeError("API Connection Timeout")

    engine.ai_client = MockFailedClient()
    engine.index_error_log("1", "Database connection timeout", "db-service")
    
    analysis = await engine.generate_root_cause_analysis_async("Database connection timeout")
    assert "[FALLBACK ANALYSIS]" in analysis
    assert engine.metrics["llm_errors"] == 1