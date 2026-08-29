import json
import os
import re
import traceback
import uuid
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from utils import (
    APP_DIR,
    RELEVANCE_THRESHOLD,
    RERANK_CANDIDATES,
    TOP_K,
    WEB_SEARCH_TOOL_SCHEMA,
    append_to_session,
    build_context,
    clear_session,
    embed_text,
    generate_hypothetical_answer,
    get_collection,
    get_llm_client,
    get_reranker,
    get_session_history,
    rerank_chunks,
    retrieve_chunks,
    trim_session,
    web_search,
)
 
from dotenv import load_dotenv
load_dotenv()


LOCAL_LLM_BASE_URL = os.environ.get("LOCAL_LLM_BASE_URL")
LOCAL_LLM_MODEL = os.environ.get("LOCAL_LLM_MODEL")

SYSTEM_PROMPT = (
    "You are a helpful florist assistant. Answer the user's question using "
    "ONLY the information provided below. If it doesn't contain the answer, "
    "say you don't have that information — do not make anything up. Answer "
    "naturally and directly, as if you simply know this — never say things "
    "like 'according to the context' or 'based on the provided information'."
)

HYDE_SYSTEM_PROMPT = (
    "You are a florist expert. Write a short, plausible-sounding answer to "
    "the user's question, as if it came from a florist knowledge base. "
    "Do not say you don't know — just write your best guess answer in a few "
    "sentences. This will be used to help find real information, so focus on "
    "sounding like a real answer, not on being correct."
)

SUMMARIZE_SYSTEM_PROMPT = (
    "You are summarizing a conversation between a user and a florist "
    "assistant. Given the previous summary (if any) and the newly dropped "
    "turns, write one short, updated summary that captures only the "
    "important context needed for future turns. Only include facts, names, "
    "and events that are explicitly stated in the provided text — never "
    "invent or assume details that are not present. Keep it concise — a "
    "few sentences."
)

WEB_SEARCH_QUERY_SYSTEM_PROMPT = (
    "The local flower knowledge base has no relevant information for the "
    "user's question. Call the web_search tool with a concise, well-formed, "
    "standalone search query that captures what the user is asking — "
    "rewrite follow-ups (e.g. 'what about roses?') into a self-contained "
    "query using the conversation so far."
)

ROUTING_SYSTEM_PROMPT = (
    "You are a routing classifier for a florist assistant. Respond with ONLY "
    "a JSON object of the exact shape {\"route\": \"...\"} and nothing else — "
    "no explanation, no markdown, no extra text. The \"route\" value must be "
    "exactly one of: \"out_of_context\", \"direct\", \"continue\".\n\n"
    "Definitions:\n"
    "- \"out_of_context\": the user's latest message is not about flowers or "
    "floristry at all, and has no reasonable connection to the conversation "
    "history shown to you (e.g. general trivia, coding help, unrelated "
    "small talk about other topics).\n"
    "- \"direct\": the message is a greeting, small talk, a question about "
    "who/what the assistant is or can do, thanks, or a follow-up that is "
    "fully answerable from the conversation history already shown to you "
    "without needing any new flower knowledge (example: 'expand on that').\n"
    "- \"continue\": the message needs real flower/floristry knowledge to "
    "answer (facts, recommendations, compatibility, care, symbolism, etc.) "
    "that isn't already fully covered by the history shown to you.\n\n"
    "Default to \"continue\" when unsure. Respond with the JSON object only."
)

OUT_OF_CONTEXT_MESSAGE = (
    "This is a flower chat bot — I can only help with flower and "
    "floristry questions."
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(asyncio.to_thread(get_collection))
    asyncio.create_task(asyncio.to_thread(get_reranker))
    yield


app = FastAPI(lifespan=lifespan)


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


@app.post("/chat")
def chat(request: ChatRequest):
    collection = get_collection()
    client = get_llm_client(LOCAL_LLM_BASE_URL)

    session_id = request.session_id or str(uuid.uuid4())

    history = get_session_history(session_id)

    routing_messages = (
        [{"role": "system", "content": ROUTING_SYSTEM_PROMPT}]
        + history
        + [{"role": "user", "content": request.question}]
    )
    routing_response = client.chat.completions.create(
        model=LOCAL_LLM_MODEL,
        messages=routing_messages,
        temperature=0,
        max_tokens=20,
    )
    raw_routing_content = routing_response.choices[0].message.content or ""

    route = None
    try:
        parsed = json.loads(raw_routing_content)
        candidate = parsed.get("route")
        if candidate in ("out_of_context", "direct", "continue"):
            route = candidate
    except (json.JSONDecodeError, AttributeError):
        pass

    if route is None:
        match = re.search(r'"route"\s*:\s*"(\w+)"', raw_routing_content)
        if match and match.group(1) in ("out_of_context", "direct", "continue"):
            route = match.group(1)

    if route is None:
        route = "continue"

    if route == "out_of_context":
        return {
            "answer": OUT_OF_CONTEXT_MESSAGE,
            "sources": [],
            "session_id": session_id,
            "source": "out_of_context",
        }

    if route == "direct":
        source = "direct"
        sources = []

        messages = (
            [{"role": "system", "content": SYSTEM_PROMPT}]
            + history
            + [{"role": "user", "content": request.question}]
        )

        response = client.chat.completions.create(
            model=LOCAL_LLM_MODEL,
            messages=messages,
        )
        answer = response.choices[0].message.content

        append_to_session(session_id, "user", request.question)
        append_to_session(session_id, "assistant", answer)

        trim_session(session_id, client, LOCAL_LLM_MODEL, SUMMARIZE_SYSTEM_PROMPT)

        return {
            "answer": answer,
            "sources": sources,
            "session_id": session_id,
            "source": source,
        }

    hyde_history = history[-4:]  # last 2 turns (user+assistant each)

    hypothetical_answer = generate_hypothetical_answer(
        request.question, client, LOCAL_LLM_MODEL, HYDE_SYSTEM_PROMPT, history=hyde_history
    )

    query_embedding = embed_text(hypothetical_answer)
 
    candidates = retrieve_chunks(
        collection,
        request.question,
        n_results=RERANK_CANDIDATES,
        query_embedding=query_embedding,
    )

    scored_chunks = rerank_chunks(request.question, candidates)
    relevant_chunks = [
        chunk for chunk, score in scored_chunks if score >= RELEVANCE_THRESHOLD
    ][:TOP_K]

    if relevant_chunks:
        source = "docs"
        context = build_context(relevant_chunks)
        sources = [
            {"source": meta.get("source"), "section": meta.get("section")}
            for _, meta, _ in relevant_chunks
        ]
    else:
        source = "web"
        print("[DEBUG] Relevance threshold not met — falling back to web search")

        try:
            query_messages = (
                [{"role": "system", "content": WEB_SEARCH_QUERY_SYSTEM_PROMPT}]
                + history
                + [{"role": "user", "content": request.question}]
            )

            tool_response = client.chat.completions.create(
                model=LOCAL_LLM_MODEL,
                messages=query_messages,
                tools=[WEB_SEARCH_TOOL_SCHEMA],
                tool_choice="required",
                temperature=0,
                max_tokens=30,
            )

            message = tool_response.choices[0].message
            if message.tool_calls:
                search_query = json.loads(message.tool_calls[0].function.arguments)["query"]
            else:
                raw = message.content or ""
                match = re.search(r'"query"\s*:\s*"([^"]+)"', raw)
                search_query = match.group(1) if match else request.question

            print(f"[DEBUG] search_query = {search_query!r}")

            results = web_search(search_query)

            context = "\n\n".join(f"{r['snippet']} (source: {r['url']})" for r in results)
            sources = [{"url": r["url"]} for r in results]
        except Exception:
            print("[DEBUG] Exception in web-fallback branch:")
            traceback.print_exc()
            raise

    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + history
        + [
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {request.question}",
            }
        ]
    )

    response = client.chat.completions.create(
        model=LOCAL_LLM_MODEL,
        messages=messages,
    )

    answer = response.choices[0].message.content

    append_to_session(session_id, "user", request.question)
    append_to_session(session_id, "assistant", answer)

    trim_session(session_id, client, LOCAL_LLM_MODEL, SUMMARIZE_SYSTEM_PROMPT)

    return {
        "answer": answer,
        "sources": sources,
        "session_id": session_id,
        "source": source,
    }


@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}


app.mount("/", StaticFiles(directory=str(APP_DIR / "static"), html=True), name="static")