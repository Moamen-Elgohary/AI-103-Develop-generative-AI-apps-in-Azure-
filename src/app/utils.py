import os
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()


APP_DIR = Path(__file__).resolve().parent
CHROMA_PATH = APP_DIR / "chroma_db"
COLLECTION_NAME = "flower_pedia"
TOP_K = 3

EMBEDDING_MODEL_NAME = os.environ.get(
    "EMBEDDING_MODEL_NAME", "sentence-transformers/all-mpnet-base-v2"
)

LOCAL_LLM_BASE_URL = os.environ.get("LOCAL_LLM_BASE_URL")
LOCAL_LLM_MODEL = os.environ.get("LOCAL_LLM_MODEL")

def get_embedding_function():
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL_NAME
    )


def get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=get_embedding_function(),
    )


def get_llm_client(base_url):
    return OpenAI(base_url=base_url, api_key="ollama")


def retrieve_chunks(collection, question, n_results=TOP_K):
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