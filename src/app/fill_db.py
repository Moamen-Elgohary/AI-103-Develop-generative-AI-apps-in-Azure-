import csv

from langchain_text_splitters import MarkdownHeaderTextSplitter

from utils import APP_DIR, get_collection

DATA_DIR = APP_DIR / "data"


def load_markdown_file(file_path, splitter):
    """Split a markdown file into H2-based chunks. Returns (documents, metadatas, ids)."""
    documents = []
    metadatas = []
    ids = []

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

    return documents, metadatas, ids


def load_csv_file(file_path):
    """Turn each CSV row into one chunk. Returns (documents, metadatas, ids)."""
    documents = []
    metadatas = []
    ids = []

    with file_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        if not fieldnames:
            return documents, metadatas, ids

        first_column = fieldnames[0]

        for index, row in enumerate(reader):
            # Skip fully empty rows.
            if not any((value or "").strip() for value in row.values()):
                continue

            row_identifier = (row.get(first_column) or "").strip() or f"row {index}"

            content = ", ".join(
                f"{col}: {(row.get(col) or '').strip()}" for col in fieldnames
            )
            content = f"{row_identifier}\n{content}"

            meta = {
                "source": file_path.name,
                "section": row_identifier,
            }

            documents.append(content)
            metadatas.append(meta)
            ids.append(f"{file_path.stem}-{index}")

    return documents, metadatas, ids


def build_collection():
    collection = get_collection()

    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=[("##", "section")])

    documents = []
    metadatas = []
    ids = []

    markdown_files = sorted(DATA_DIR.glob("*.md"))
    csv_files = sorted(DATA_DIR.glob("*.csv"))

    if not markdown_files and not csv_files:
        raise FileNotFoundError(f"No markdown or CSV files found in: {DATA_DIR}")

    for file_path in markdown_files:
        file_documents, file_metadatas, file_ids = load_markdown_file(file_path, splitter)
        documents.extend(file_documents)
        metadatas.extend(file_metadatas)
        ids.extend(file_ids)

    for file_path in csv_files:
        file_documents, file_metadatas, file_ids = load_csv_file(file_path)
        documents.extend(file_documents)
        metadatas.extend(file_metadatas)
        ids.extend(file_ids)

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