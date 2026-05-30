"""Knowledge retriever — gets relevant context from vector store."""

from src.knowledge.vector_store import InMemoryVectorStore


class KnowledgeRetriever:
    def __init__(self):
        self.store = InMemoryVectorStore()

    async def get_relevant_context(self, query: str) -> str:
        results = await self.store.search(query, top_k=3)
        if not results:
            return ""
        sections = []
        for r in results:
            sections.append(f"[{r['metadata'].get('source', 'knowledge')}]: {r['content']}")
        return "\n\n".join(sections)

    async def ingest_runbook(self, doc_id: str, content: str, source: str = "runbook") -> None:
        await self.store.add_document(doc_id, content, {"source": source})
