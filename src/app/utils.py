import os
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from sentence_transformers import CrossEncoder

from dotenv import load_dotenv
load_dotenv()


APP_DIR = Path(__file__).resolve().parent
CHROMA_PATH = APP_DIR / "chroma_db"
COLLECTION_NAME = "flower_pedia"
TOP_K = 3
RERANK_CANDIDATES = 10

EMBEDDING_MODEL_NAME = os.environ.get(
    "EMBEDDING_MODEL_NAME", "sentence-transformers/all-mpnet-base-v2"
)

RERANKER_MODEL_NAME = os.environ.get(
    "RERANKER_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

LOCAL_LLM_BASE_URL = os.environ.get("LOCAL_LLM_BASE_URL")
LOCAL_LLM_MODEL = os.environ.get("LOCAL_LLM_MODEL")


_embedding_fn = None
_collection = None
_reranker = None
SESSIONS = {}


def get_embedding_function():
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL_NAME
        )
    return _embedding_fn


def embed_text(text):
    embedding_fn = get_embedding_function()
    return embedding_fn([text])[0] 

 
def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=get_embedding_function(),
        )
    return _collection

 
def get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(RERANKER_MODEL_NAME)
    return _reranker


def get_llm_client(base_url):
    return OpenAI(base_url=base_url, api_key="ollama")


def retrieve_chunks(collection, question, n_results=TOP_K, query_embedding=None):
    if query_embedding is not None:
        results = collection.query(query_embeddings=[query_embedding], n_results=n_results)
    else:
        results = collection.query(query_texts=[question], n_results=n_results)
 
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    return list(zip(docs, metas, distances))


def build_context(chunks):
    parts = []
    for doc, meta, _ in chunks:
        source = meta.get("source", "unknown")
        section = meta.get("section", "unknown")
        parts.append(f"[{source} - {section}]\n{doc}")
    return "\n\n".join(parts)


def generate_hypothetical_answer(question, client, model, system_prompt, history=None):
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
    )
    return response.choices[0].message.content


def rerank_chunks(question, chunks, top_n=TOP_K):
    if not chunks:
        return chunks
 
    reranker = get_reranker()
    pairs = [(question, doc) for doc, _, _ in chunks]
    scores = reranker.predict(pairs)
 
    reranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    return [chunk for chunk, _ in reranked[:top_n]]


def get_session_history(session_id):
    return SESSIONS.get(session_id, [])
 
 
def append_to_session(session_id, role, content):
    SESSIONS.setdefault(session_id, []).append({"role": role, "content": content})
 
 
def clear_session(session_id):
    SESSIONS.pop(session_id, None)