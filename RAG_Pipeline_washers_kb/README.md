# MegaWasher RAG App


## Project Links

[Documentation](https://docs.google.com/document/d/1UxR1Wpt8PjF3Yl5VHa8RpFMtSpVUAz8KTxyUZBsHRBE/edit?tab=t.0)

[Sample data](./kb_washers_01.json)

[Demo](https://www.loom.com/share/317e2ab3b43341cb8514752e1a22163f)

## Project Description

MegaWash RAG App helps customers answer customer support questions from the internal Knowledge Base (support tickets + FAQ documents + product manuals).

An ingestion program written in Python will take the data and perform extraction, fragmentation into chunks, embedding , indexing and saving the resulting vector data into a PineCone vector database. 

The retrieval will be done by a Hybrid Retriever application written in Python that will perform hybrid (semantic / BM25 keywords). The semantic search will be done by making calls to the PineCone vector database. Top-k value will be 3.

## Architecture

```
React UI (frontend/, Vite)  --POST /api/ask-->  FastAPI (api.py)  -->  HybridRAG (rag_service.py)
                                                                          |-- Pinecone (semantic search)
                                                                          |-- BM25 (keyword search)
                                                                          `-- OpenAI gpt-4.1-mini (answer)
```

| File | Purpose |
|------|---------|
| `ingest.py` | Chunks and embeds the KB and stores the vectors in Pinecone |
| `rag_service.py` | Shared hybrid retrieval + answer generation (`HybridRAG.ask`) |
| `retriever_hybrid.py` | Command-line version of the Q&A tool |
| `api.py` | FastAPI REST API |
| `frontend/` | React web UI |

## Setup

Requirements: Python 3.12+ with [uv](https://docs.astral.sh/uv/), and Node.js 20+.

1. Create `.env` in this folder with `OPENAI_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` and `PINECONE_NAMESPACE`.
2. Install the dependencies:
```
uv sync
cd frontend
npm install
```

## Run Ingestion App

The Ingestion app only needs to be run once, or every time the Knowledge Base data (json) changes.
```
uv run ingest.py
```

## Run Retrieval App (command line)
```
uv run retriever_hybrid.py
```

## Run the Web App

Start the backend and the frontend in two terminals.

**1. Backend (FastAPI)**, from this folder:
```
uv run uvicorn api:app --reload --port 8000
```
Interactive API docs: http://localhost:8000/docs

**2. Frontend (React)**, from `frontend/`:
```
npm run dev
```
Open http://localhost:5173

### API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | `{"status": "ok", "rag_ready": true}` once the pipeline is loaded |
| POST | `/api/ask` | Body `{"question": "..."}` (3-1000 chars). Returns `{question, answer, citations[]}`; each citation has `ticket_id`, `title`, `doc_type`, `product_area`, `product_type`, `snippet` |

Example:
```
curl -X POST http://localhost:8000/api/ask -H "Content-Type: application/json" -d "{\"question\": \"My washer won't drain\"}"
```

### Configuration

| Variable | Where | Default | Purpose |
|----------|-------|---------|---------|
| `VITE_API_URL` | `frontend/.env` | `http://localhost:8000` | Backend URL the UI calls (copy `frontend/.env.example`) |
| `CORS_ORIGINS` | `.env` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated origins allowed to call the API |

### Troubleshooting

- **"Cannot reach the API"** in the UI: make sure the backend is running and that `VITE_API_URL` matches its port. Restart `npm run dev` after editing `frontend/.env`.
- **Port 8000 already in use** (`Errno 10048`): stop the program using it, or run uvicorn with `--port 8010` and set `VITE_API_URL=http://localhost:8010`.
- **CORS error in the browser console**: add the frontend's origin to `CORS_ORIGINS`.

## Sample user query

You can use the User Query below to test the Retriever app:

My front load washer door won't open. What can I do?
