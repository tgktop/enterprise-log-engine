import os
import chromadb
from google import genai

class LogVectorEngine:
    def __init__(self, db_path: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="error_logs")
        
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            self.ai_client = genai.Client(api_key=self.api_key)
        else:
            self.ai_client = None

    def index_error_log(self, log_id: str, error_message: str, service_name: str) -> None:
        if not error_message or not error_message.strip():
            return
            
        self.collection.add(
            documents=[error_message],
            metadatas=[{"service": service_name}],
            ids=[str(log_id)]
        )

    def query_similar_errors(self, query: str, n_results: int = 3) -> dict:
        total_docs = self.collection.count()
        if total_docs == 0:
            return {"documents": [[]], "metadatas": [[]]}
            
        return self.collection.query(
            query_texts=[query],
            n_results=min(n_results, total_docs)
        )

    def generate_root_cause_analysis(self, query: str) -> str:
        if not self.ai_client:
            return f"[MOCK ANALYSIS] Synthetic root cause for: '{query}'. Set GEMINI_API_KEY to enable LLM."

        matches = self.query_similar_errors(query)
        documents = matches.get("documents", [[]])[0]
        metadatas = matches.get("metadatas", [[]])[0]

        if not documents:
            return "No matching error logs found in vector index to analyze."

        context_blocks = []
        for doc, meta in zip(documents, metadatas):
            service = meta.get("service", "unknown-service") if meta else "unknown-service"
            context_blocks.append(f"Service: [{service}] | Log: {doc}")

        context = "\n".join(context_blocks)
        
        prompt = (
            "You are a Principal Site Reliability Engineer (SRE).\n"
            f"Incident Query: '{query}'\n\n"
            f"Retrieved Log Context:\n{context}\n\n"
            "Task: Provide a concise root cause analysis and explicit mitigation steps."
        )

        response = self.ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text