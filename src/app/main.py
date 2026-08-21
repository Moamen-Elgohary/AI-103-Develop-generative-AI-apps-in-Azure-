import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from utils import (
    APP_DIR,
    build_context,
    get_collection,
    get_llm_client,
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

app = FastAPI()


class ChatRequest(BaseModel):
    question: str


@app.post("/chat")
def chat(request: ChatRequest):
    collection = get_collection()
    chunks = retrieve_chunks(collection, request.question)
    context = build_context(chunks)

    client = get_llm_client(LOCAL_LLM_BASE_URL)
    response = client.chat.completions.create(
        model=LOCAL_LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {request.question}",
            },
        ],
    )

    answer = response.choices[0].message.content
    sources = [
        {"source": meta.get("source"), "section": meta.get("section")}
        for _, meta, _ in chunks
    ]

    return {"answer": answer, "sources": sources}


app.mount("/", StaticFiles(directory=str(APP_DIR / "static"), html=True), name="static")