"""Vector store abstraction for RAG over runbooks, docs, and incidents."""

from abc import ABC, abstractmethod


class VectorStore(ABC):
    @abstractmethod
    async def add_document(self, doc_id: str, content: str, metadata: dict | None = None) -> None:
        ...

    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        ...

    @abstractmethod
    async def delete(self, doc_id: str) -> None:
        ...


class InMemoryVectorStore(VectorStore):
    def __init__(self):
        self._docs: dict[str, dict] = {}

    async def add_document(self, doc_id: str, content: str, metadata: dict | None = None) -> None:
        self._docs[doc_id] = {"content": content, "metadata": metadata or {}}

    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        query_lower = query.lower()
        scored = []
        for doc_id, doc in self._docs.items():
            content_lower = doc["content"].lower()
            score = sum(1 for word in query_lower.split() if word in content_lower)
            if score > 0:
                scored.append((score, {"id": doc_id, "content": doc["content"][:500], "metadata": doc["metadata"]}))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:top_k]]

    async def delete(self, doc_id: str) -> None:
        self._docs.pop(doc_id, None)
