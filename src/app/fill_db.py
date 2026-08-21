from langchain_text_splitters import MarkdownHeaderTextSplitter

from utils import APP_DIR, get_collection

DATA_DIR = APP_DIR / "data"


def build_collection():
    collection = get_collection()

    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=[("##", "section")])

    documents = []
    metadatas = []
    ids = []

    markdown_files = sorted(DATA_DIR.glob("*.md"))
    if not markdown_files:
        raise FileNotFoundError(f"No markdown files found in: {DATA_DIR}")

    for file_path in markdown_files:
        text = file_path.read_text(encoding="utf-8")
        chunks = splitter.split_text(text)

        for index, chunk in enumerate(chunks):
            content = chunk.page_content.strip()
            if not content:
                continue

            meta = dict(chunk.metadata)
            meta["source"] = file_path.name
            meta["section"] = meta.get("section", "overview")

            # Prepend section name so it's part of the embedded text,
            # not just metadata.
            content = f"{meta['section']}\n{content}"

            documents.append(content)
            metadatas.append(meta)
            ids.append(f"{file_path.stem}-{index}")

    if not documents:
        raise ValueError(f"No content was extracted from files in: {DATA_DIR}")

    collection.upsert(
        documents=documents,
        metadatas=metadatas,
        ids=ids,
    )

    print(f"Loaded {len(documents)} chunks into Chroma collection.")


if __name__ == "__main__":
    build_collection()