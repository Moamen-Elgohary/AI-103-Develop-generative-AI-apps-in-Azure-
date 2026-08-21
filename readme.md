# RAG Flower Chatbot with Web Search Fallback

A chatbot that answers primarily from your own documents (RAG), falling back to live web search when local knowledge isn't sufficient. Built on top of the AI-103 Foundry SDK / Responses API material.

## Concept

Ask it things like:
- "What should I know before buying tulips?"
- "Can I put roses and carnations in the same vase?"
- "What flowers should I avoid mixing with lilies?"

## Stack (Grand Plan / Target)

- **LLM**: Azure OpenAI via Responses API
- **Embeddings**: `text-embedding-3-small` (Azure OpenAI)
- **Vector DB**: Chroma (local for v1, Azure AI Search later)
- **Chunking**: LangChain `MarkdownHeaderTextSplitter`
- **Web search fallback**: `web_search` tool
- **Backend**: FastAPI
- **Frontend**: Basic HTML/CSS/JS (v1), improved later

> **Note:** v1 uses local equivalents for LLM and embeddings, and stays local through HyDE (v2) and reranking (v3) since both are free — see [Roadmap](#roadmap) and [v1 — Core RAG](#v1--core-rag-local-only-completed) for what's actually running today.

## Roadmap

### v1 — Core RAG (local only) — ✅ Completed
- Load MDs → chunk → embed → store in Chroma
- FastAPI backend, single `/chat` endpoint
- Basic styled HTML/JS frontend
- No memory, no web search — just "ask your docs"

### v2 — HyDE retrieval
- LLM generates a hypothetical answer to the question first
- Embed that hypothetical answer (not the raw question) and use it to query Chroma
- Stays fully local (local LLM + local embeddings)

### v3 — Reranking
- Retrieve a larger top-k candidate set from Chroma
- Add a local reranker (e.g. cross-encoder like `bge-reranker` or MiniLM MS MARCO) to reorder candidates by relevance
- Pass only top reranked chunks to the LLM as context
- Stays fully local

### v4 — Add memory
- Session-based conversation tracking (`previous_response_id` or manual history)
- Multi-turn context in the UI

### v5 — Add web search fallback
- If RAG retrieval score is low, trigger `web_search` tool
- UI shows source: "from your docs" vs "from the web"

### v6 — Multi-document management
- Upload documents via UI (not just pre-loaded files)
- Delete/re-index documents
- Show which document a chunk came from (citations in UI)

### v7 — Cloud LLM & Embeddings swap
- Swap local LLM → Azure OpenAI (Responses API)
- Swap local embeddings → `text-embedding-3-small` (Azure OpenAI)
- Update `.env` / config for Azure credentials and endpoints

### v8 — Polish & UX
- Streaming responses in the UI (typing effect)
- Better frontend (React or improved HTML/CSS)
- Error handling, loading states

### v9 — Production readiness (end goal)
- Swap Chroma → Azure AI Search (cloud-hosted vector DB)
- Deploy FastAPI backend to Azure (App Service or Container Apps)
- Auth (basic login or API key protection)
- Logging/monitoring
- Deployed, shareable link

## End Goal

A deployed, cloud-hosted RAG chatbot with web search fallback, multi-document support, streaming UI, and proper auth — a complete showcase project demonstrating the full AI-103 skill set in a real app.

---

## v1 — Core RAG (local only) — Completed

To avoid over-scoping, v1 cut everything down to the smallest working loop.

### v1 Actual Stack
- **LLM**: Local model via OpenAI-compatible client (Ollama), using `chat.completions.create`
- **Embeddings**: Local `sentence-transformers/all-mpnet-base-v2` via Chroma's built-in embedding function
- **Vector DB**: Chroma (persistent local client)
- **Chunking**: LangChain `MarkdownHeaderTextSplitter` (split on `##` → `section`)
- **Backend**: FastAPI, single `/chat` endpoint
- **Frontend**: Lightly styled HTML/JS (chat bubbles, custom font) — more polished than originally scoped "text box only," but still v1-simple: no memory, no streaming, no multi-turn

### v1 Source Files

| File | Purpose | Source |
|---|---|---|
| `flower_symbolism.md` | Flower to meaning lookup | Wikipedia: "List of plants with symbolism" |
| `flower_compatibility.md` | Vase life, ethylene sensitivity, sap toxicity, bad pairings | Written by us, based on public florist/horticulture sources |

### v1 Files

| File | Purpose |
|---|---|
| `utils.py` | Shared helpers — embedding function, Chroma collection getter, LLM client getter, chunk retrieval, context building |
| `fill_db.py` | Loads and chunks source `.md` files, embeds them, upserts into Chroma collection |
| `main.py` | FastAPI app — `/chat` endpoint, serves static frontend |
| `query_db.py` | CLI dev/debug tool — query the Chroma collection directly and inspect retrieved chunks/distances |
| `index.html` | Frontend — chat UI (input box, bubbles, fetch to `/chat`) |

### v1 Build Steps (Completed)
1. Prepared the two source files (clean markdown/text)
2. Chunked each file (`MarkdownHeaderTextSplitter`)
3. Embedded chunks using local `sentence-transformers/all-mpnet-base-v2` and stored in Chroma
4. Built FastAPI backend: single `/chat` endpoint — takes a question, retrieves top-k chunks, calls local LLM with retrieved context, returns the answer
5. Built minimal styled HTML/JS frontend: input box, submit button, response display
6. Added `query_db.py` for local retrieval testing/debugging
7. Tested end-to-end locally