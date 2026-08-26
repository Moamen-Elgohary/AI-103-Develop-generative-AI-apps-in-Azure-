import os
import uuid
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from utils import (
    APP_DIR,
    RERANK_CANDIDATES,
    TOP_K,
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
)
 
from dotenv import load_dotenv
load_dotenv()


LOCAL_LLM_BASE_URL = os.environ.get("LOCAL_LLM_BASE_URL")
LOCAL_LLM_MODEL = os.environ.get("LOCAL_LLM_MODEL")

SYSTEM_PROMPT = (
    "You are a helpful florist assistant. Answer the user's question using "
    "ONLY the context provided below. If the context doesn't contain the "
    "answer, say you don't have that information — do not make anything up."
)

HYDE_SYSTEM_PROMPT = (
    "You are a florist expert. Write a short, plausible-sounding answer to "
    "the user's question, as if it came from a florist knowledge base. "
    "Do not say you don't know — just write your best guess answer in a few "
    "sentences. This will be used to help find real information, so focus on "
    "sounding like a real answer, not on being correct."
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
    hyde_history = history[-4:]

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

    chunks = rerank_chunks(request.question, candidates, top_n=TOP_K)
    context = build_context(chunks)

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

    sources = [
        {"source": meta.get("source"), "section": meta.get("section")}
        for _, meta, _ in chunks
    ]

    append_to_session(session_id, "user", request.question)
    append_to_session(session_id, "assistant", answer)

    return {"answer": answer, "sources": sources, "session_id": session_id}


@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}


app.mount("/", StaticFiles(directory=str(APP_DIR / "static"), html=True), name="static")