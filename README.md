# Enterprise Log RAG Engine

An asynchronous Retrieval-Augmented Generation (RAG) log analysis engine built in Python. Designed to automate Site Reliability Engineering (SRE) incident triage by vectorizing error logs, filtering noisy data, and leveraging Google Gemini for root cause analysis.

## Core Features
* **Non-Blocking Async Pipeline:** Fully asynchronous query and analysis methods utilizing `asyncio.to_thread` for background task delegation.
* **Context Hygiene & Distance Thresholding:** Automatically filters out irrelevant vector distance matches to prevent LLM hallucination and context pollution.
* **Smart Stack-Trace Truncation:** Preserves top-level exception signatures and bottom-frame tracebacks while safely pruning middle noise.
* **Structured Metadata Filtering:** Supports payload isolation by microservice, timestamp, and environment (`production` vs. `staging`).
* **Robust Fallback & Telemetry:** Gracefully handles external API outages and tracks internal execution metrics.

## Tech Stack
* **Language:** Python 3.13
* **Vector Database:** ChromaDB (Persistent Client)
* **LLM SDK:** Google GenAI SDK (`gemini-2.5-flash`)
* **Testing:** Pytest & Pytest-Asyncio

## Project Structure
```text
enterprise-log-engine/
├── rag_engine.py       # Core asynchronous vector RAG engine
├── test_engine.py      # Automated async test suite
├── .env.example        # Environment variable template
└── README.md           # Project documentation
