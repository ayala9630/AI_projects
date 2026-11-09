"""Search over the chunks: by meaning (vectors), by words (BM25), and the two combined."""
from netfree_unstrict_ssl import unstrict_ssl
unstrict_ssl()
import re
import json
from rag.model_client import chat_completion
import numpy as np
from rank_bm25 import BM25Okapi

from rag.chunking import Chunk
from rag.embed import Embedder

def tokenize(text: str) -> list[str]:
    # Keeps codes like "of-450h" and "e-26" as single tokens.
    return re.findall(r"[\w-]+", text.lower())


class Index:
    def __init__(self, chunks: list[Chunk], embedder: Embedder):
        self.chunks = chunks
        self.embedder = embedder
        self.vectors = embedder.embed([c.text for c in chunks], "passage")
        self.bm25 = BM25Okapi([tokenize(c.text) for c in chunks])

    def vector_search(self, query: str, k: int = 50) -> list[int]:
        """Indexes of the k chunks closest in meaning to the query, best first."""
        q = self.embedder.embed([query], "query")[0]
        scores = self.vectors @ q
        return [int(i) for i in np.argsort(-scores)[:k]]

    def bm25_search(self, query: str, k: int = 50) -> list[int]:
        """Indexes of the k chunks with the best word match, best first."""
        scores = self.bm25.get_scores(tokenize(query))
        return [int(i) for i in np.argsort(-scores)[:k] if scores[i] > 0]

def rrf(rankings: list[list[int]], k: int = 60) -> list[int]:
    scores = {}

    for ranking in rankings:
        for rank, chunk_index in enumerate(ranking, start=1):
            scores[chunk_index] = (
                scores.get(chunk_index, 0) +
                1 / (k + rank)
            )

    return sorted(
        scores,
        key=lambda chunk_index: scores[chunk_index],
        reverse=True
    )


def is_current(chunk: Chunk) -> bool:
    return chunk.meta.get("status") != "superseded"


def search(index: Index, query: str, mode: str = "vector", top_k: int = 5,
           current_only: bool = False) -> list[Chunk]:
    if mode == "vector":
        ranked = index.vector_search(query)
    elif mode == "hybrid":
        ranked = rrf([index.vector_search(query), index.bm25_search(query)])
    else:
        raise ValueError(f"unknown mode: {mode}")
    if current_only:
        ranked = [i for i in ranked if is_current(index.chunks[i])]
    return [index.chunks[i] for i in ranked[:top_k]]
def expand_query(question: str) -> list[str]:
    """
    Converts a complex question into focused retrieval queries.
    A regular question returns one query.
    A comparison question returns one query per entity.
    """

    response = chat_completion(
        messages=[
            {
                "role": "system",
                "content": """
You are a query expansion component for a RAG system.

Analyze the user's question and generate focused search queries.

Rules:
1. For a simple question, return one search query.
2. For a comparison question, return a separate query
   for each entity being compared.
3. Preserve exact product names, model names and identifiers.
4. Do not answer the question.
5. Do not invent entities or facts.
6. Return only valid JSON in this exact structure:

{
  "queries": [
    "search query 1",
    "search query 2"
  ]
}
"""
            },
            {
                "role": "user",
                "content": question
            }
        ],
        response_format={"type": "json_object"},
        temperature=0
    )

    data = json.loads(response.choices[0].message.content)

    queries = data.get("queries", [])

    if not isinstance(queries, list) or not queries:
        return [question]

    queries = [
        q.strip()
        for q in queries
        if isinstance(q, str) and q.strip()
    ]

    return queries or [question]

def expanded_search(
    index,
    question: str,
    mode: str = "hybrid",
    k: int = 3,
    current_only: bool = False
):
    queries = expand_query(question)

    results = []
    seen = set()

    for query in queries:
        chunks = search(
            index,
            query,
            mode,
            k,
            current_only
        )

        for chunk in chunks:
            if chunk.id not in seen:
                seen.add(chunk.id)
                results.append(chunk)

    return results