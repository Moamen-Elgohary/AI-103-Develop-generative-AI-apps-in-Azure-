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
    """Run one question through retrieval (+ optional HyDE/rerank) and print
    a compact, threshold-relevant summary. Returns the top normalized rerank
    score (or None if --rerank wasn't used), so callers can build a
    cross-question summary for picking RELEVANCE_THRESHOLD.
    """
    query_embedding = None

    if use_hyde:
        client = get_llm_client(LOCAL_LLM_BASE_URL)
        hypothetical_answer = generate_hypothetical_answer(
            question, client, LOCAL_LLM_MODEL, HYDE_SYSTEM_PROMPT
        )
        query_embedding = embed_text(hypothetical_answer)

    candidate_n = RERANK_CANDIDATES if use_rerank else n_results
    chunks = retrieve_chunks(
        collection, question, candidate_n, query_embedding=query_embedding
    )

    if not use_rerank:
        print(f"\nQ: {question}")
        if not chunks:
            print("  (no results)")
            return None
        for i, (doc, meta, dist) in enumerate(chunks, start=1):
            source = meta.get("source", "unknown")
            section = meta.get("section", "unknown")
            print(f"  {i}. distance={dist:.4f}  {source} / {section}")
        return None

    scored_chunks = rerank_chunks(question, chunks)

    print(f"\nQ: {question}")
    if not scored_chunks:
        print("  (no results)")
        return None

    top_score = scored_chunks[0][1]
    second_score = scored_chunks[1][1] if len(scored_chunks) > 1 else 0.0
    gap = top_score - second_score

    print(f"  top={top_score:.4f}  2nd={second_score:.4f}  gap={gap:.4f}")
    for i, ((doc, meta, dist), score) in enumerate(scored_chunks[:n_results], start=1):
        source = meta.get("source", "unknown")
        section = meta.get("section", "unknown")
        print(f"  {i}. score={score:.4f}  {source} / {section}")

    return top_score


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

    print("Enter questions one at a time. Leave blank (or type 'quit') to stop and see the summary.\n")

    summary = []
    while True:
        try:
            question = input("Ask a question: ").strip()
        except EOFError:
            break
        if not question or question.lower() == "quit":
            break
        top_score = query(collection, question, use_hyde=args.hyde, use_rerank=args.rerank)
        if args.rerank:
            summary.append((question, top_score))

    if args.rerank and summary:
        print("\n" + "=" * 60)
        print("SUMMARY — top score per question, sorted high to low")
        print("=" * 60)
        for question, top_score in sorted(summary, key=lambda x: x[1], reverse=True):
            print(f"  {top_score:.4f}   {question}")
        print(
            "\nLook for the natural gap between questions your docs should "
            "answer and ones they shouldn't — set RELEVANCE_THRESHOLD in "
            "that gap."
        )


if __name__ == "__main__":
    main()