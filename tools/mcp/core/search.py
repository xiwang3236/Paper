"""
Semantic search over the paper knowledge base.
"""

import json
from typing import Optional

from .database import get_collection


def search_papers(
    query: str,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    platform: Optional[str] = None,
    n_results: int = 8,
) -> list[dict]:
    """Run semantic search across the paper repository."""
    collection = get_collection()
    count = collection.count()
    if count == 0:
        return []

    where_clauses = []
    if year_min:
        where_clauses.append({"year": {"$gte": year_min}})
    if year_max:
        where_clauses.append({"year": {"$lte": year_max}})
    if platform:
        where_clauses.append({"platform": {"$contains": platform}})

    where = None
    if len(where_clauses) > 1:
        where = {"$and": where_clauses}
    elif where_clauses:
        where = where_clauses[0]

    kwargs = {
        "query_texts": [query],
        "n_results": min(n_results, count),
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    output = []
    for i, doc_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i]
        output.append({
            "id": doc_id,
            "title": meta.get("title", "Unknown"),
            "authors": meta.get("authors", ""),
            "year": meta.get("year") or None,
            "section": meta.get("section", ""),
            "text_chunk": results["documents"][0][i],
            "distance": round(results["distances"][0][i], 4),
            "doi": meta.get("doi", ""),
            "assignment": meta.get("assignment", ""),
            "modalities": meta.get("modalities", ""),
            "platform": meta.get("platform", ""),
            "topics": json.loads(meta.get("topics", "[]")),
        })

    return output
