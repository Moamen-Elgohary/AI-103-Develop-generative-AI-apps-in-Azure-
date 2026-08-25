import argparse
import os

from utils import (
    RERANK_CANDIDATES,
    embed_text,
    generate_hypothetical_answer,
    get_collection,
    get_llm_client,
    rerank_chunks,
    retrieve_chunks,
)

from dotenv import load_dotenv
load_dotenv()

LOCAL_LLM_BASE_URL = os.environ.get("LOCAL_LLM_BASE_URL")
LOCAL_LLM_MODEL = os.environ.get("LOCAL_LLM_MODEL")

HYDE_SYSTEM_PROMPT = (
    "You are a florist expert. Write a short, plausible-sounding answer to "
    "the user's question, as if it came from a florist knowledge base. "
    "Do not say you don't know — just write your best guess answer in a few "
    "sentences. This will be used to help find real information, so focus on "
    "sounding like a real answer, not on being correct."
)


def query(collection, question, n_results=3, use_hyde=False, use_rerank=False):
    query_embedding = None

    if use_hyde:
        client = get_llm_client(LOCAL_LLM_BASE_URL)
        hypothetical_answer = generate_hypothetical_answer(
            question, client, LOCAL_LLM_MODEL, HYDE_SYSTEM_PROMPT
        )
        query_embedding = embed_text(hypothetical_answer)
        print(f"  [HyDE hypothetical answer]: {hypothetical_answer[:200]}...\n")

    candidate_n = RERANK_CANDIDATES if use_rerank else n_results
    chunks = retrieve_chunks(
        collection, question, candidate_n, query_embedding=query_embedding
    )

    if use_rerank:
        print(f"\n  [Candidates before rerank: {len(chunks)}]")
        for i, (doc, meta, dist) in enumerate(chunks, start=1):
            source = meta.get("source", "unknown")
            section = meta.get("section", "unknown")
            print(f"    [{i}] source={source} section={section} distance={dist:.4f}")
            print(f"        {doc[:150]}{'...' if len(doc) > 150 else ''}")
        chunks = rerank_chunks(question, chunks, top_n=n_results)
        print(f"\n  [Top {len(chunks)} after rerank]")

    mode_parts = []
    mode_parts.append("HyDE" if use_hyde else "raw question")
    if use_rerank:
        mode_parts.append("rerank")
    mode = "+".join(mode_parts)
    print(f"  (mode: {mode})")

    if not chunks:
        print("  (no results)")
        return

    for i, (doc, meta, dist) in enumerate(chunks, start=1):
        source = meta.get("source", "unknown")
        section = meta.get("section", "unknown")
        print(f"  [{i}] source={source} section={section} distance={dist:.4f}")
        print(f"      {doc[:200]}{'...' if len(doc) > 200 else ''}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--hyde", action="store_true", help="Use HyDE retrieval instead of raw question"
    )
    parser.add_argument(
        "--rerank", action="store_true", help="Rerank retrieved candidates with a cross-encoder"
    )
    args = parser.parse_args()

    collection = get_collection()
    question = input("Ask a question: ")
    query(collection, question, use_hyde=args.hyde, use_rerank=args.rerank)


if __name__ == "__main__":
    main()