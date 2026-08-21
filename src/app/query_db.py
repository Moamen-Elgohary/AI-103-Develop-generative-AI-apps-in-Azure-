from utils import get_collection, retrieve_chunks


def query(collection, question, n_results=3):
    chunks = retrieve_chunks(collection, question, n_results)
 
    if not chunks:
        print("  (no results)")
        return
 
    for i, (doc, meta, dist) in enumerate(chunks, start=1):
        source = meta.get("source", "unknown")
        section = meta.get("section", "unknown")
        print(f"  [{i}] source={source} section={section} distance={dist:.4f}")
        print(f"      {doc[:200]}{'...' if len(doc) > 200 else ''}")


def main():
    collection = get_collection()
    question = input("Ask a question: ")
    query(collection, question)


if __name__ == "__main__":
    main()