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

> **Note:** v1 uses local equivalents for LLM and embeddings, and stays local through HyDE (v2) and reranking (v3, both completed) since both are free — see [Roadmap](#roadmap) and [v1 — Core RAG](#v1--core-rag-local-only-completed) for what's actually running today.

## Roadmap

### v1 — Core RAG (local only) — ✅ Completed
- Load MDs → chunk → embed → store in Chroma
- FastAPI backend, single `/chat` endpoint
- Basic styled HTML/JS frontend
- No memory, no web search — just "ask your docs"

### v2 — HyDE retrieval — ✅ Completed
- LLM generates a hypothetical answer to the question first
- Embed that hypothetical answer (not the raw question) and use it to query Chroma
- Stays fully local (local LLM + local embeddings)

### v3 — Reranking — ✅ Completed
- Retrieve a larger top-k candidate set from Chroma
- Add a local reranker (e.g. cross-encoder like `bge-reranker` or MiniLM MS MARCO) to reorder candidates by relevance
- Pass only top reranked chunks to the LLM as context
- Stays fully local

### v4 — Add memory 
- Session-based conversation tracking
- Multi-turn context in the UI
- v4.1 — HyDE hypothetical-answer generation considers recent conversation history, not just the latest question
- v4.2 — Summarize-and-drop older turns once history exceeds a limit, to bound token cost on long sessions

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

### v1 Stack
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

### v1 Build Steps
1. Prepared the two source files (clean markdown/text)
2. Chunked each file (`MarkdownHeaderTextSplitter`)
3. Embedded chunks using local `sentence-transformers/all-mpnet-base-v2` and stored in Chroma
4. Built FastAPI backend: single `/chat` endpoint — takes a question, retrieves top-k chunks, calls local LLM with retrieved context, returns the answer
5. Built minimal styled HTML/JS frontend: input box, submit button, response display
6. Added `query_db.py` for local retrieval testing/debugging
7. Tested end-to-end locally

---
 
## v2 — HyDE Retrieval — Completed
 
**What:** Before embedding the user's question, ask the local LLM to generate a hypothetical (made-up) answer. Embed that hypothetical answer instead of the raw question, then use it to query Chroma. Hypothetical answers resemble real document chunks more closely than bare questions do, improving retrieval match quality.
 
### v2 Stack, Source files
- Same as v1 — no new dependencies

### v2 Files
 
| File | Purpose |
|---|---|
| `utils.py` | Modified — added `generate_hypothetical_answer()` and `embed_text()`; `retrieve_chunks()` now accepts an optional `query_embedding` param |
| `main.py` | Modified — defines `HYDE_SYSTEM_PROMPT`; `/chat` now generates a hypothetical answer, embeds it, and retrieves with that embedding before the final LLM call |
| `query_db.py` | Modified — defines `HYDE_SYSTEM_PROMPT`; added `--hyde` CLI flag to compare HyDE vs raw-query retrieval |
 
### v2 Build Steps
1. Added `generate_hypothetical_answer(question, client, model, system_prompt)` to `utils.py` — LLM generates a hypothetical answer from the user's question
2. Added `embed_text(text)` to `utils.py` — embeds arbitrary text using the same local embedding function (`all-mpnet-base-v2`)
3. Modified `retrieve_chunks()` in `utils.py` to accept an optional `query_embedding` — uses it via `collection.query(query_embeddings=...)` if provided, falls back to raw-question `query_texts` otherwise (backward compatible)
4. Updated `/chat` in `main.py`: question → HyDE generation → embed → retrieve → build context → final LLM call
5. Added `--hyde` flag to `query_db.py` to test HyDE vs raw-query retrieval side-by-side, printing the mode and hypothetical answer used
6. Tested end-to-end: `query_db.py --hyde` vs `query_db.py` for retrieval comparison, and full `/chat` flow via `uvicorn main:app --reload`

---
 
## v3 — Reranking — Completed
 
**What:** HyDE (v2) retrieves a candidate set using an embedding of a hypothetical prose answer, which can bias against short/structured content and doesn't always surface the most relevant chunks in the right order. Reranking adds a second pass: retrieve a wider candidate pool from Chroma, then use a cross-encoder to score each candidate directly against the raw question and reorder by true relevance before building context.
 
**Ties into v2** widening the initial top-k and reranking against the raw question (not the HyDE embedding) helps recover relevant chunks — including structured/CSV rows, if added later — that HyDE's prose bias may have ranked lower. Reranking fixes ordering/precision within the retrieved pool; it can't recover chunks HyDE excluded entirely, so top-k width still matters.
 
### v3 Stack
- Same as v2 — one new dependency: a local cross-encoder reranker (e.g. `cross-encoder/ms-marco-MiniLM-L-6-v2` via `sentence-transformers`, likely already available as it's part of the `sentence-transformers` package)
- **LLM**: Local model via Ollama (unchanged)
- **Embeddings**: Local `sentence-transformers/all-mpnet-base-v2` (unchanged)
- **Reranker**: Local cross-encoder (new)
- **Vector DB**: Chroma (unchanged)

### v3 Files
 
| File | Purpose |
|---|---|
| `utils.py` | Modified — add `get_reranker()` (lazy-load-with-cache, same pattern as embedding model) and `rerank_chunks(question, chunks, top_n)` |
| `main.py` | Modified — `lifespan` background-loads reranker alongside embedding model; `/chat` retrieves a wider candidate pool, reranks, then builds context from top reranked chunks |
| `query_db.py` | Modified — add `--rerank` flag to compare raw vs HyDE vs HyDE+rerank retrieval side-by-side |
 
### v3 Build Steps
1. Add `get_reranker()` to `utils.py` — lazy-load a local cross-encoder model, cached after first load (same pattern as `get_embedding_function()`)
2. Add `rerank_chunks(question, chunks, top_n)` to `utils.py` — scores each (question, chunk) pair with the cross-encoder, sorts descending, returns top `top_n`
3. Widen initial retrieval: increase `n_results` in the `retrieve_chunks()` call (e.g. top_k=10 candidates) before reranking down to a smaller final set (e.g. top 3)
4. Update `lifespan` in `main.py` to also background-load the reranker at startup (alongside the embedding model)
5. Update `/chat` in `main.py`: HyDE-embed → retrieve wide candidate pool → rerank with raw question → build context from top reranked chunks → final LLM call
6. Add `--rerank` flag to `query_db.py` to compare raw / HyDE / HyDE+rerank retrieval side-by-side
7. Test retrieval quality: check whether reranking recovers relevant chunks that HyDE's prose bias ranked lower

---

## v4 — Add Memory — Completed

**What:** Track conversation history per session so follow-up questions have context. Uses manual history (list of messages sent on every call), not `previous_response_id` — that's a Responses API feature and this stack runs on `chat.completions.create` via Ollama, which is stateless per call.

### v4 Stack
- Same as v3 — no new dependencies (in-memory session store, no DB)

### v4 Files

| File | Purpose |
|---|---|
| `utils.py` | Modified — add in-memory `SESSIONS` dict, `get_session_history(session_id)` / `append_to_session(session_id, role, content)` / `clear_session(session_id)` helpers |
| `main.py` | Modified — `ChatRequest` gains optional `session_id`; generates a new one if absent; builds LLM messages as system prompt + prior history + new question; appends question/answer to session after response; returns `session_id` in response; adds `DELETE /session/{session_id}` endpoint to clear a session's history |
| `index.html` | Modified — stores `session_id` in a JS variable after first response, sends it on subsequent `/chat` calls; adds a "New Session" button that clears local `session_id` and chat UI, and tells the backend to drop that session's history |

### v4 Build Steps
1. Add `SESSIONS = {}` to `utils.py` — in-memory dict mapping `session_id` → list of message dicts
2. Add `get_session_history(session_id)` (using `.get(session_id, [])` so an unknown ID returns empty history instead of erroring), `append_to_session(session_id, role, content)`, and `clear_session(session_id)` helpers to `utils.py`
3. Update `ChatRequest` in `main.py` to accept optional `session_id`; generate a new UUID if not provided
4. Update `/chat` in `main.py`: build final LLM call's `messages` as system prompt + full session history + new user question (HyDE/retrieval stay unchanged — based on the latest question only, as in v3)
5. After getting the answer, append the user question and assistant answer to that session's history
6. Return `session_id` in the `/chat` response so the frontend can persist and resend it
7. Add `DELETE /session/{session_id}` endpoint in `main.py` calling `clear_session()`
8. Update `index.html`: store `session_id` from the first response, include it in the body of subsequent `/chat` POSTs
9. Add a "New Session" button to `index.html` — on click, calls `DELETE /session/{session_id}` (if one exists), clears the local `session_id` variable, and clears the chat bubble UI
10. Test multi-turn flow: ask a question, then a follow-up that depends on prior context, confirm the LLM sees history
11. Test reset: start a session, ask a follow-up, click "New Session", confirm next question gets no prior context and UI is empty

---

## v4.1 — HyDE-Aware History (Planned)

**Design discussion — should HyDE see prior history?**

The open question was whether `generate_hypothetical_answer()` should only take the latest question, or the question plus recent conversation history.

The problem: v4 memory only helps the *final* LLM call — retrieval happens *before* that, via HyDE, and still only sees the latest question in isolation. A follow-up like "What about roses?" gives HyDE nothing to anchor on. HyDE would generate a generic hypothetical about roses in general, missing whatever the conversation was actually about (e.g. vase compatibility, toxicity). Retrieval then queries Chroma with that ungrounded hypothetical and pulls back irrelevant chunks — so the follow-up looks broken at the retrieval step even though memory "works" at the chat-history level.

The fix isn't to hand HyDE the *entire* session history either. Full history adds tokens per call for no real benefit, and older turns can dilute the hypothetical answer with context that's no longer relevant to the current question.

**Decision:** `generate_hypothetical_answer()` takes the latest question plus the last 2 turns of history if available (fewer if the session has less). This keeps HyDE grounded on follow-ups without paying for or diluting on irrelevant older context.

### v4.1 Files (Planned)

| File | Purpose |
|---|---|
| `utils.py` | Modified — `generate_hypothetical_answer()` now accepts recent-history turns (latest 2 if available) and includes them in the prompt |
| `main.py` | Modified — `/chat` passes the latest question + last 2 turns of session history (if available) into `generate_hypothetical_answer()` |

### v4.1 Build Steps (Planned)
1. Update `generate_hypothetical_answer()` in `utils.py` to accept optional recent-history turns and include them in the prompt to the LLM
2. Update `/chat` in `main.py`: pass the latest question + last 2 turns of session history (if available) into `generate_hypothetical_answer()`
3. Test: ask a question, then a follow-up like "what about roses?", confirm HyDE's hypothetical answer reflects the prior turn's context and retrieval pulls relevant chunks

---

## v4.2 — History Trimming (Planned)

**Design discussion — trimming**

The problem: session history has no cap. If someone chats for 50 turns, every `/chat` call sends the *full* history to the LLM — cost and latency creep the longer a conversation runs, even on local Ollama.

**Decision:** summarize-and-drop. Once history exceeds N turns, collapse the older turns into a short LLM-generated summary and keep that summary plus the recent raw turns, instead of sending everything forever. This gives the best context retention of the options considered, at the cost of an extra LLM call and added complexity — arguably overkill for a local Ollama chatbot, but it avoids losing older context entirely the way a hard cutoff would.

To keep the summary itself from growing unbounded as a long session keeps triggering trims, each trim regenerates the summary from scratch rather than appending to it: the old summary plus the newly-dropped turns are fed into the LLM together and replaced with one fresh summary. This keeps the summary roughly the same size no matter how long the session runs, instead of turning into a summary-of-a-summary-of-a-summary that grows forever.

Trimming only ever removes the *oldest* excess turns from `turns`, never the most recent ones — so v4.1's HyDE lookup (last 2 turns) always reads from the untrimmed recent tail and is unaffected by trimming.

### v4.2 Files (Planned)

| File | Purpose |
|---|---|
| `utils.py` | Modified — add `HISTORY_TURN_LIMIT` constant and `summarize_history()`; session storage shape changes to `{"summary": str | None, "turns": [...]}`; `append_to_session()` triggers a trim when `turns` exceeds the limit; `get_session_history()` prepends the summary as a system message when one exists |
| `main.py` | No changes — trimming is internal to `utils.py`'s session helpers |

### v4.2 Build Steps (Planned)
1. Add `HISTORY_TURN_LIMIT` constant and a summarization system prompt to `utils.py`
2. Change session storage shape to `{"summary": None, "turns": []}` per session
3. Add `summarize_history(old_summary, dropped_turns, client, model, system_prompt)` to `utils.py` — feeds the old summary (if any) plus newly-dropped turns into the LLM, returns one fresh summary
4. Update `append_to_session()` — after appending, if `len(turns) > HISTORY_TURN_LIMIT`, pull the oldest excess turns, call `summarize_history()`, replace `summary`, drop those turns from `turns`
5. Update `get_session_history()` — return `[{"role": "system", "content": f"Earlier conversation summary: {summary}"}] + turns` when a summary exists, else just `turns`
6. Test: chat past the turn limit, confirm older turns get summarized and dropped while recent turns and the summary are still passed to the LLM