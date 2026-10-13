from __future__ import annotations
from pathlib import Path
from typing import Any
import chromadb
from chromadb.utils import embedding_functions
from .data_loader import Leaflet, load_leaflets

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def get_collection(chroma_dir: str, collection_name: str):
    Path(chroma_dir).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=chroma_dir)
    emb = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=DEFAULT_EMBEDDING_MODEL
    )
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=emb,
        metadata={"hnsw:space": "cosine"},
    )


def build_index(leaflets_dir: str, chroma_dir: str, collection_name: str, reset: bool = False) -> int:
    client = chromadb.PersistentClient(path=chroma_dir)
    if reset:
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass
    emb = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=DEFAULT_EMBEDDING_MODEL
    )
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=emb,
        metadata={"hnsw:space": "cosine"},
    )
    leaflets = load_leaflets(leaflets_dir)
    if collection.count() == len(leaflets) and not reset:
        return collection.count()

    ids = [x.doc_id for x in leaflets]
    docs = [f"{x.title}\n{x.text}" for x in leaflets]
    metas = [{"title": x.title, "source": x.source, "path": x.path} for x in leaflets]
    collection.upsert(ids=ids, documents=docs, metadatas=metas)
    return collection.count()


def retrieve(query: str, chroma_dir: str, collection_name: str, top_k: int = 3) -> list[dict[str, Any]]:
    collection = get_collection(chroma_dir, collection_name)
    result = collection.query(query_texts=[query], n_results=top_k)
    hits: list[dict[str, Any]] = []
    for i, doc_id in enumerate(result.get("ids", [[]])[0]):
        distance = result.get("distances", [[]])[0][i]
        meta = result.get("metadatas", [[]])[0][i]
        doc = result.get("documents", [[]])[0][i]
        hits.append({
            "rank": i + 1,
            "doc_id": doc_id,
            "score": round(1 - float(distance), 4),
            "title": meta.get("title", doc_id),
            "source": meta.get("source", "unknown"),
            "path": meta.get("path", ""),
            "text": doc,
        })
    return hits

