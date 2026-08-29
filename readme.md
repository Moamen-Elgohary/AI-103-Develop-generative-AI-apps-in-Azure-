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

### v4 — Add memory — ✅ Completed
- Session-based conversation tracking
- Multi-turn context in the UI
- v4.1 — HyDE hypothetical-answer generation considers recent conversation history, not just the latest question
- v4.2 — Summarize-and-drop older turns once history exceeds a limit, to bound token cost on long sessions

### v5 — Relevance-Gated Retrieval + Web Search Fallback — ✅ Completed
- Reranker scores are kept and normalized (0-1), instead of discarded after picking top-k
- Chunks are filtered by a relevance threshold (tuned to `0.03` against ~80 test questions), capped at `TOP_K`
- If nothing clears the threshold, the LLM is forced (`tool_choice="required"`) to call a `web_search` tool with its own reformulated query, with a text-parsing fallback for local models that don't honor forced tool calls
- A routing step also catches greetings/small talk/meta questions and history-only follow-ups ("expand on that"), answering directly without docs or web
- UI shows source: "from your docs" vs "from the web" (no tag for direct answers)

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

## v4.1 — HyDE-Aware History — Completed
**Design discussion — should HyDE see prior history?**

The open question was whether `generate_hypothetical_answer()` should only take the latest question, or the question plus recent conversation history.

The problem: v4 memory only helps the *final* LLM call — retrieval happens *before* that, via HyDE, and still only sees the latest question in isolation. A follow-up like "What about roses?" gives HyDE nothing to anchor on. HyDE would generate a generic hypothetical about roses in general, missing whatever the conversation was actually about (e.g. vase compatibility, toxicity). Retrieval then queries Chroma with that ungrounded hypothetical and pulls back irrelevant chunks — so the follow-up looks broken at the retrieval step even though memory "works" at the chat-history level.

The fix isn't to hand HyDE the *entire* session history either. Full history adds tokens per call for no real benefit, and older turns can dilute the hypothetical answer with context that's no longer relevant to the current question.

**Decision:** `generate_hypothetical_answer()` takes the latest question plus the last 2 turns of history if available (fewer if the session has less). This keeps HyDE grounded on follow-ups without paying for or diluting on irrelevant older context.

### v4.1 Files

| File | Purpose |
|---|---|
| `utils.py` | Modified — `generate_hypothetical_answer()` now accepts recent-history turns (latest 2 if available) and includes them in the prompt |
| `main.py` | Modified — `/chat` passes the latest question + last 2 turns of session history (if available) into `generate_hypothetical_answer()` |

### v4.1 Build Steps (Planned)
1. Update `generate_hypothetical_answer()` in `utils.py` to accept optional recent-history turns and include them in the prompt to the LLM
2. Update `/chat` in `main.py`: pass the latest question + last 2 turns of session history (if available) into `generate_hypothetical_answer()`
3. Test: ask a question, then a follow-up like "what about roses?", confirm HyDE's hypothetical answer reflects the prior turn's context and retrieval pulls relevant chunks

---

## v4.2 — History Trimming — Completed
 
**Design discussion — trimming**
 
The problem: session history has no cap. If someone chats for many turns, every `/chat` call sends the *full* history to the LLM — cost and latency creep the longer a conversation runs, even on local Ollama.
 
**Decision:** summarize-and-drop. Once `turns` exceeds `HISTORY_TURN_LIMIT`, collapse everything except the last 4 messages (2 user+assistant pairs) into a short LLM-generated summary, and keep that summary plus those last 4 raw turns — instead of sending everything forever.
 
To keep the summary itself from growing unbounded as a long session keeps triggering trims, each trim regenerates the summary from scratch rather than appending to it: the old summary plus the newly-dropped turns are fed into the LLM together and replaced with one fresh summary. This keeps the summary roughly the same size no matter how long the session runs, instead of turning into a summary-of-a-summary-of-a-summary that grows forever.
 
`append_to_session()` appends a single message (role + content) to the session's `turns` list. A separate `trim_session()` function is called once per turn, from `main.py`, only after *both* the user question and assistant answer have been appended. It checks whether `turns` has exceeded `HISTORY_TURN_LIMIT`, and only when that's true does it make a summarization LLM call — most turns don't trigger it at all, and trimming only ever happens at a pair boundary.
 
Trimming always keeps the last 4 messages (2 full turns) untouched, since v4.1's HyDE lookup reads from that same tail — this guarantees HyDE's lookback window is never affected by trimming.
 
**Hallucination fix:** early testing showed the summarization call could invent details (names, settings, events) not present in the actual conversation, and — since each trim re-feeds the previous summary back in — a hallucination could persist and compound across trims. Fixed by setting `temperature=0` and `max_tokens=250` on the summarization call, and tightening `SUMMARIZE_SYSTEM_PROMPT` to explicitly forbid including anything not explicitly stated in the source turns.
 
### v4.2 Files
 
| File | Purpose |
|---|---|
| `utils.py` | Modified — add `HISTORY_TURN_LIMIT` constant; add `summarize_history(old_summary, dropped_turns, client, model, system_prompt)` (`temperature=0`, `max_tokens=250`); session storage shape changes to `{"summary": str \| None, "turns": [...]}`; `append_to_session()` appends a message to `turns`; new `trim_session(session_id, client, model, summarize_system_prompt, keep_last=4)` checks the limit and, if exceeded, summarizes everything except the last `keep_last` messages; `get_session_history()` prepends the summary as a system message when one exists |
| `main.py` | Modified — defines `SUMMARIZE_SYSTEM_PROMPT` (alongside `SYSTEM_PROMPT`/`HYDE_SYSTEM_PROMPT`, explicitly forbids inventing details); calls `trim_session()` once per turn, right after both `append_to_session()` calls |
 
### v4.2 Build Steps
1. Add `HISTORY_TURN_LIMIT` constant to `utils.py`; add `SUMMARIZE_SYSTEM_PROMPT` to `main.py` (kept alongside the other prompts for consistency)
2. Change session storage shape to `{"summary": None, "turns": []}` per session
3. Add `summarize_history(old_summary, dropped_turns, client, model, system_prompt)` to `utils.py` — feeds the old summary (if any) plus newly-dropped turns into the LLM with `temperature=0` and `max_tokens=250`, returns one fresh summary
4. `append_to_session()` in `utils.py` appends a single message (role + content) to the session's `turns` list
5. Add `trim_session(session_id, client, model, summarize_system_prompt, keep_last=4)` to `utils.py` — if `len(turns) > HISTORY_TURN_LIMIT`, summarizes everything except the last `keep_last` messages, replaces `summary`, keeps only the last `keep_last` in `turns`
6. Update `get_session_history()` — return `[{"role": "system", "content": f"Earlier conversation summary: {summary}"}] + turns` when a summary exists, else just `turns`
7. Call `trim_session()` in `main.py`, once per turn, immediately after both `append_to_session()` calls (user question + assistant answer) — guarantees trimming only ever happens at a pair boundary
8. Tighten `SUMMARIZE_SYSTEM_PROMPT` to forbid inventing facts/names/events not explicitly present in the source turns, after observing hallucinated details compounding across trims
9. Test: chat past the turn limit, confirm older turns get summarized (accurately, no invented details) and dropped while the last 4 raw turns and the summary are still passed to the LLM and to HyDE

---

## v5 — Relevance-Gated Retrieval with Web Search Fallback — Completed

**What:** v3's reranker always hands the LLM a fixed top-3 chunks, regardless of whether they're actually relevant to the question. v5 makes relevance a measurable, filterable signal — so the number of chunks used reflects real document coverage — and adds a web search fallback for questions local docs don't cover at all. Along the way, testing surfaced a second gap (routing every turn through docs-or-web breaks on greetings and follow-ups), which got folded into this version too.

### Approach
- Reranker scores every candidate chunk against the question (already happens in v3) — the score is kept instead of discarded
- Scores are normalized to 0-1 (sigmoid) so the threshold can be tuned by eye
- Chunks are filtered by `RELEVANCE_THRESHOLD`, capped at `TOP_K` — 0 to 3 chunks depending on actual relevance, not always 3
- If nothing clears the threshold, a web search is triggered instead of forcing an answer from weak context
- Each response is tagged `source: "docs"`, `"web"`, or `"direct"` so the frontend can show where the answer came from

**Why the reranker score, not Chroma's raw distance:** Chroma's distance is tied to the embedding model's vector space and has no fixed range — it will also change when v7 swaps embeddings. The reranker score is already computed, question-specific, and reusable for both the chunk-count decision and the fallback trigger — one signal, two uses.

### Threshold tuning — what actually happened

The original plan was to eyeball a threshold from a handful of test questions. In practice this took a larger batch to get right:

1. **First 3 questions** suggested real matches scored ~0.08–0.98 and irrelevant ones scored ~0.0000 — a clean, wide gap.
2. **A larger batch (~80 questions)** across both docs, deliberately including borderline and out-of-scope cases, confirmed the same pattern held at scale: genuine matches consistently scored well above the confirmed noise floor (`0.0000`) from every out-of-scope test question.

**Decision:** `RELEVANCE_THRESHOLD = 0.03`. This sits below the normal range of true positives and comfortably above the confirmed noise floor. Tuned using `query_db.py` (see below) against ~80 real questions, not the placeholder guess from the original plan.

**Sample results**, spanning the full score range from the tuning run (full set in `questions.txt`):

| Score | Question | Doc |
|---|---|---|
| 0.9997 | What's the meaning of a peony? | symbolism |
| 0.9950 | What does euphorbia sap do to other flowers? | compatibility |
| 0.9803 | What flowers should I use for a funeral arrangement? | symbolism |
| 0.9394 | What's the best way to recut flower stems? | compatibility |
| 0.7927 | How can I make my cut flowers last longer? | compatibility |
| 0.6878 | What's the meaning behind giving someone a sunflower? | symbolism |
| 0.4338 | What flowers are toxic to cats? | compatibility |
| 0.3212 | Which flowers work well as an anchor in a mixed bouquet? | compatibility |
| 0.1675 | What flowers should I avoid giving for a somber occasion? | symbolism |
| **0.0944** | Why shouldn't I put roses and carnations in the same vase? | compatibility |
| **0.0813** | What flowers should I avoid mixing with lilies? | compatibility |
| — *threshold = 0.03* — | | |
| 0.0000 | Who won the last World Cup? | *n/a* |
| 0.0000 | What's the capital of France? | *n/a* |
| 0.0000 | How do I fix a Python import error? | *n/a* |

### How the web search fallback works
When nothing clears the threshold, the raw user question isn't searched directly — the LLM is asked to write the search query itself, since it can phrase follow-ups (e.g. "what about roses?") into a proper standalone query.

This uses tool calling: the LLM is given a `web_search` function tool and `tool_choice="required"`, forcing it to use the tool rather than answer directly, with `temperature=0` and `max_tokens=30` since only a short, precise search phrase is needed. The returned query is run through `web_search()` (using `duckduckgo-search`), and the results are formatted as plain context text fed into the same shared final-answer LLM call used by the docs path (see "Simplification" below) — no separate web-only system prompt, no tool-call/tool-result message replay.

Ollama has no hosted search capability, so the model can only *request* a search via a function tool — execution and feeding results back happens in application code. This mirrors the shape a future hosted-tool version (e.g. Azure OpenAI's `{"type": "web_search"}`) would take, so this design doubles as practice for that later swap — only the model and search backend change, not the shape.

**Reliability gap found during testing:** `tool_choice="required"` isn't consistently honored by Ollama's OpenAI-compatible endpoint — `llama3.2:3b` was observed echoing its attempted tool call as malformed JSON text in `content` instead of populating `tool_calls`, crashing the original implementation (`tool_calls[0]` on `None`). Fixed with a fallback: if `message.tool_calls` is empty, regex-scrape a `"query": "..."` pattern out of `content`, falling back to the raw question if even that fails. This keeps the primary path matching Azure's real tool-call shape and only degrades gracefully for local models that don't honor the forced call.


### Routing gap found during testing — direct-answer path
Testing surfaced a case the docs-or-web split didn't handle: a bare follow-up like "expand on that" has no semantic content of its own, so it fails the relevance threshold regardless of whether the docs actually cover the topic, and gets misrouted to web search. The same problem showed up for greetings and meta questions ("hi", "who are you") — especially on the very first turn, with no history to fall back on either.

**Fix:** a third route, checked before HyDE/retrieval run at all. One LLM call (`ROUTING_SYSTEM_PROMPT`, `temperature=0`, `max_tokens=2`) decides YES/NO: can this turn be answered directly from conversation history and general ability, with no new flower knowledge or web search needed? YES routes to a direct answer using the same `SYSTEM_PROMPT` + history, tagged `source = "direct"`, skipping HyDE/retrieval/rerank/web entirely. NO falls through to the existing docs → threshold → web flow, unchanged.

**Known limitation:** `llama3.2:3b` doesn't always follow the "respond with exactly one word" instruction. The prompt went through several rounds of tightening to improve this. Parsing stays conservative regardless: only a response starting with `YES` counts as `YES`; anything else defaults to `NO` and falls through to the normal docs/web flow, so a misfire costs an unnecessary lookup, never a blocked answer. Occasional misroutes on unusual phrasing are still possible. Revisiting with a smaller model dedicated to routing only (e.g. one with stronger structured-output reliability) is a candidate follow-up, not yet done.

### v5 Stack (additions)
- `duckduckgo-search` for web fallback

### v5 Files

| File | Purpose |
|---|---|
| `utils.py` | `rerank_chunks()` returns all scored chunks (normalized 0-1), not just top-n; adds `RELEVANCE_THRESHOLD = 0.03`; adds `WEB_SEARCH_TOOL_SCHEMA`; adds `web_search(query, max_results=3)` using `duckduckgo-search` |
| `main.py` | Adds a routing step (`ROUTING_SYSTEM_PROMPT`) before HyDE/retrieval, for direct/history-only answers (`source = "direct"`); filters reranked chunks by threshold, capped at `TOP_K`; empty → forced tool call (with text-parsing fallback for local models) → execute search → shared final-answer call; `source` (`"docs"` \| `"web"` \| `"direct"`) added to response |
| `query_db.py` | Rewritten as a looping CLI tool (reads questions until blank/EOF, so input can be piped from a file) — prints per-question `top`/`2nd`/`gap` scores plus a full end-of-session summary sorted by score, for threshold tuning |
| `questions.txt` | Combined batch of ~80 test questions (in-scope, borderline, out-of-scope) used to tune `RELEVANCE_THRESHOLD`; pipe into `query_db.py --hyde --rerank < questions.txt` to reproduce |
| `index.html` | Shows "from your docs" / "from the web" tag per answer bubble; no tag shown for `"direct"` answers |

### v5 Build Steps (as completed)
1. Sigmoid-normalize reranker scores in `rerank_chunks()`; return all scored chunks, sorted
2. Add `RELEVANCE_THRESHOLD` constant (placeholder, tuned later)
3. Define `WEB_SEARCH_TOOL_SCHEMA` (name: `web_search`, param: `query: string`)
4. Add `duckduckgo-search` dependency; add `web_search(query, max_results=3)` → list of `{snippet, url}`
5. In `/chat`: filter scored chunks by threshold, cap at `TOP_K`
6. Chunks found → existing flow, `source = "docs"`
7. Empty → LLM call with `tools=[WEB_SEARCH_TOOL_SCHEMA]`, `tool_choice="required"`, `temperature=0`, `max_tokens=30`; added a fallback for when `tool_calls` comes back empty (local model reliability issue, see above)
8. Parse the tool call's (or fallback-parsed) query
9. Run `web_search(query)`
10. Format results as plain context text; feed into the same shared final-answer call used by the docs path (simplified from the original tool-call/tool-result message replay plan)
11. Set `source = "web"`
12. Rewrite `query_db.py` into a looping, pipeable CLI tool that prints per-question scores and an end-of-session summary
13. Run ~80 test questions (mixed in-scope, borderline, out-of-scope) through `query_db.py`; tune `RELEVANCE_THRESHOLD` to `0.03` based on the results
14. Update `index.html` to render the source tag
15. Add the routing step (`ROUTING_SYSTEM_PROMPT`) for direct/history-only answers, discovered as a necessary addition during testing (see above)
16. Test: docs path unaffected; no-chunk path triggers forced tool call and falls back gracefully when the local model doesn't honor it; greetings and simple follow-ups route to `"direct"` without hitting docs/web; a real docs question still routes correctly afterward