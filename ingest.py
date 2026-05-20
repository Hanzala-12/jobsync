import os
import json
import glob
import uuid
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import chromadb

load_dotenv()

SEED_DIR = os.path.join(os.getcwd(), "seed_data")
PERSIST_DIR = os.path.join(os.getcwd(), "chroma_db")
COLLECTION_NAME = "jobfit_docs"

# Simple character-based chunker
def chunk_text(text, chunk_size=800, overlap=200):
    if not text:
        return []
    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

def load_seed_files(seed_dir=SEED_DIR):
    docs = []
    os.makedirs(seed_dir, exist_ok=True)
    patterns = ["*.json", "*.txt"]
    files = []
    for p in patterns:
        files.extend(glob.glob(os.path.join(seed_dir, p)))

    for fpath in files:
        name = os.path.basename(fpath)
        try:
            if fpath.lower().endswith('.json'):
                with open(fpath, 'r', encoding='utf-8') as f:
                    j = json.load(f)
                    text = j.get('text') or j.get('content') or ''
                    metadata = j.get('metadata', {})
            else:
                with open(fpath, 'r', encoding='utf-8') as f:
                    text = f.read()
                    metadata = {"source": name}
            if not text:
                continue
            docs.append({"id": str(uuid.uuid4()), "text": text, "metadata": metadata})
        except Exception as e:
            print(f"Failed to load {fpath}: {e}")
    return docs

def main():
    print("Starting ingestion...")
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

    client = chromadb.PersistentClient(path=PERSIST_DIR)
    collection = client.get_or_create_collection(COLLECTION_NAME)

    docs = load_seed_files()
    if not docs:
        print(f"No seed documents found in {SEED_DIR}. Place .txt or .json files there.")
        return

    ids, metadatas, documents, embeddings = [], [], [], []
    for d in docs:
        chunks = chunk_text(d['text'])
        for i, c in enumerate(chunks):
            doc_id = f"{d['id']}_{i}"
            ids.append(doc_id)
            md = dict(d.get('metadata', {}))
            md.update({"source_id": d['id'], "chunk_index": i})
            metadatas.append(md)
            documents.append(c)

    print(f"Computing embeddings for {len(documents)} chunks...")
    # sentence-transformers returns numpy arrays; convert to lists
    embs = model.encode(documents, show_progress_bar=True, convert_to_numpy=True)
    embeddings = [e.tolist() for e in embs]

    print(f"Upserting into Chroma ({PERSIST_DIR}) collection={COLLECTION_NAME}...")
    collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
    print("Ingestion completed and persisted.")

if __name__ == '__main__':
    main()
