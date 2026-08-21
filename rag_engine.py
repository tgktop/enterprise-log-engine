import os
import chromadb

class LogVectorEngine:
    def __init__(self):
        self.client = chromadb.Client()
        self.collection = self.client.create_collection(name="error_logs")
        
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            from google import genai
            self.ai_client = genai.Client(api_key=self.api_key)

    def index_error_log(self, log_id: str, error_message: str, service_name: str):
        if not error_message:
            return
        self.collection.add(
            documents=[error_message],
            metadatas=[{"service": service_name}],
            ids=[log_id]
        )

    def query_similar_errors(self, query: str, n_results: int = 3):
        if self.collection.count() == 0:
            return []
        return self.collection.query(
            query_texts=[query],
            n_results=min(n_results, self.collection.count())
        )

    def generate_root_cause_analysis(self, query: str) -> str:
        if not self.api_key:
            return f"[MOCK ANALYSIS] Synthetic root cause generated for query: '{query}'. Set GEMINI_API_KEY in .env to enable live LLM synthesis."

        matches = self.query_similar_errors(query)
        documents = matches.get("documents", [[]])[0]

        if not documents:
            return "No matching error logs found to analyze."

        context = "\n".join([f"- {doc}" for doc in documents])
        prompt = f"""
        You are a Principal Site Reliability Engineer (SRE).
        Analyze these relevant error logs for the incident query: '{query}'

        Retrieved Logs:
        {context}

        Provide a concise root cause analysis and action steps to resolve the issue.
        """

        response = self.ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text