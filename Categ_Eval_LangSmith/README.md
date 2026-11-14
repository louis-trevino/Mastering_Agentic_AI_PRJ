# SuperGlasses Hybrid RAG App

This project contains the SuperGlasses customer-support RAG system and its React web
front end. The backend combines Pinecone semantic retrieval with local BM25 keyword
retrieval, then uses OpenAI to produce a grounded answer with source citations.

## Project layout

- `rag_service.py` — reusable hybrid retrieval and answer-generation service
- `api.py` — FastAPI endpoints used by the React app
- `retriever_hybrid.py` — interactive terminal version of the RAG workflow
- `kb_eyeglass_01.json` — local knowledge base used by BM25
- `frontend/` — React, Vite, and TypeScript web application

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Node.js 20+

## Backend setup

From the `Categ_Eval_LangSmith` directory:

```powershell
uv sync --all-groups
Copy-Item .env.example .env
```

Populate `.env` with your OpenAI and Pinecone values:

```dotenv
OPENAI_API_KEY=...
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=...
PINECONE_NAMESPACE=...
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Start the FastAPI server using the project startup script:

```powershell
.\start_backend.ps1
```

The script always uses `Categ_Eval_LangSmith` as its base directory and starts
the API at <http://localhost:8000>. API documentation is available at
<http://localhost:8000/docs>.

If PowerShell blocks local script execution for the current user, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

The interactive terminal workflow remains available:

```powershell
uv run python retriever_hybrid.py
```

## Frontend setup

From the `frontend` directory:

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

The frontend runs at <http://localhost:5173> and calls the backend at
`http://localhost:8000`. If the API runs at another address, set
`VITE_API_BASE_URL` in `frontend/.env`.

Open <http://localhost:5173> to use the assistant.
Open <http://localhost:5173> to use the assistant.
Open <http://localhost:5173> to use the assistant.

## API

### `GET /api/health`

Returns `{"status":"ok"}` when the API process is available.

### `POST /api/search`

```json
{
  "question": "How do I track my order?"
}
```

Response:

```json
{
  "question": "How do I track my order?",
  "answer": "Open your order page to view its latest status.",
  "sources": [
    {
      "title": "Order tracking",
      "content": "Open your order page to view tracking.",
      "doc_type": "support_ticket",
      "category": "order_status",
      "ticket_id": "TKT-00002"
    }
  ]
}
```

Questions must contain 3–1000 characters. API documentation is available at
<http://localhost:8000/docs>.

## Tests and validation

```powershell
# Backend
uv run pytest tests -q

# Frontend
npm test --prefix frontend
npm run lint --prefix frontend
npm run build --prefix frontend
```

## Security notes

- Never expose OpenAI or Pinecone credentials through `VITE_*` variables; Vite
  variables are sent to the browser.
- The frontend contains no credentials and communicates only with the FastAPI API.
- Set `FRONTEND_ORIGINS` to the exact deployed front-end origins in production.
