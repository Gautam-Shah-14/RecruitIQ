import chromadb
from app.config import settings

client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
collection = client.get_or_create_collection(
    name=settings.chroma_collection,
    metadata={"hnsw:space": "cosine"}  # use cosine similarity
)

def add_candidates(candidate_ids: list[str], embeddings: list[list[float]], metadatas: list[dict]):
    collection.add(
        ids=candidate_ids,
        embeddings=embeddings,
        metadatas=metadatas
    )

def query_candidates(query_embedding: list[float], top_k: int, filters: dict = None):
    where = {}
    if filters and "min_years_exp" in filters and filters["min_years_exp"] is not None:
        where["years_exp"] = {"$gte": filters["min_years_exp"]}
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where if where else None
    )
    return results
