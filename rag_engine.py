import os
import re
import time
import logging
import asyncio
from typing import Dict, Any, List, Optional
import chromadb
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("LogVectorEngine")

class LogVectorEngine:
    def __init__(
        self, 
        db_path: Optional[str] = None, 
        max_distance_threshold: float = 0.75
    ) -> None:
        if not db_path:
            db_path = os.getenv("CHROMA_DB_PATH", "./chroma_db")
            
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="error_logs")
        self.max_distance_threshold = max_distance_threshold
        
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            from google import genai
            self.ai_client = genai.Client(api_key=self.api_key)
        else:
            self.ai_client = None

        # Internal telemetry metrics
        self.metrics: Dict[str, int] = {
            "total_queries": 0,
            "cache_hits": 0,
            "llm_calls": 0,
            "llm_errors": 0
        }

    def sanitize_log(self, raw_log: str) -> str:
        """
        Cleans logs while preserving head and tail of stack traces,
        ensuring crucial exception details at the bottom are preserved.
        """
        if not raw_log or not isinstance(raw_log, str):
            return ""
            
        cleaned = re.sub(r'[\r\t]+', ' ', raw_log)
        cleaned = re.sub(r'[ ]+', ' ', cleaned).strip()
        
        if len(cleaned) > 2000:
            head = cleaned[:1000]
            tail = cleaned[-900:]
            cleaned = f"{head} ... [TRUNCATED STACKTRACE] ... {tail}"
            
        return cleaned

    def index_error_log(
        self, 
        log_id: str, 
        error_message: str, 
        service_name: str, 
        environment: str = "production",
        timestamp: Optional[int] = None
    ) -> None:
        cleaned_message = self.sanitize_log(error_message)
        if not cleaned_message:
            return
            
        metadata = {
            "service": service_name,
            "environment": environment,
            "timestamp": timestamp or int(time.time())
        }
            
        self.collection.add(
            documents=[cleaned_message],
            metadatas=[metadata],
            ids=[str(log_id)]
        )

    async def query_similar_errors_async(
        self, 
        query: str, 
        n_results: int = 3, 
        where_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[List[Any]]]:
        """Async-compatible vector query with structured metadata filtering and type safety."""
        self.metrics["total_queries"] += 1
        total_docs = self.collection.count()
        if total_docs == 0:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
            
        cleaned_query = self.sanitize_log(query)
        if not cleaned_query:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        query_kwargs: Dict[str, Any] = {
            "query_texts": [cleaned_query],
            "n_results": min(n_results, total_docs)
        }
        if where_filter:
            query_kwargs["where"] = where_filter

        raw_results = self.collection.query(**query_kwargs)

        filtered_docs: List[str] = []
        filtered_metas: List[Dict[str, Any]] = []
        filtered_dists: List[float] = []

        docs = raw_results.get("documents", [[]])[0]
        metas = raw_results.get("metadatas", [[]])[0]
        dists = raw_results.get("distances", [[]])[0]

        for doc, meta, dist in zip(docs, metas, dists):
            if dist <= self.max_distance_threshold:
                filtered_docs.append(doc)
                filtered_metas.append(meta)
                filtered_dists.append(dist)

        return {
            "documents": [filtered_docs],
            "metadatas": [filtered_metas],
            "distances": [filtered_dists]
        }

    async def generate_root_cause_analysis_async(
        self, 
        query: str, 
        where_filter: Optional[Dict[str, Any]] = None
    ) -> str:
        """Async root cause analysis leveraging non-blocking thread delegation for LLM calls."""
        if not self.ai_client:
            return f"[MOCK ANALYSIS] Synthetic root cause for: '{query}'. Set GEMINI_API_KEY to enable LLM."

        matches = await self.query_similar_errors_async(query, where_filter=where_filter)
        documents = matches.get("documents", [[]])[0]
        metadatas = matches.get("metadatas", [[]])[0]
        distances = matches.get("distances", [[]])[0]

        if not documents:
            return "No relevant error logs found in vector index within confidence threshold."

        context_blocks = []
        for doc, meta, dist in zip(documents, metadatas, distances):
            service = meta.get("service", "unknown-service") if meta else "unknown-service"
            env = meta.get("environment", "unknown-env") if meta else "unknown-env"
            context_blocks.append(f"Service: [{service}] | Env: [{env}] | Dist: {dist:.3f} | Log: {doc}")

        context = "\n".join(context_blocks)
        
        prompt = (
            "You are a Principal Site Reliability Engineer (SRE).\n"
            f"Incident Query: '{query}'\n\n"
            f"Retrieved Log Context:\n{context}\n\n"
            "Task: Provide a concise root cause analysis and explicit mitigation steps."
        )

        try:
            self.metrics["llm_calls"] += 1
            
            # Offload synchronous network call to a background worker thread
            response = await asyncio.to_thread(
                self.ai_client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
            )
            return response.text
            
        except Exception as e:
            self.metrics["llm_errors"] += 1
            logger.error(f"LLM API Call failed: {e}")
            return f"[FALLBACK ANALYSIS] Unable to reach LLM service. Relevant logs retrieved: {len(documents)}"