"""RAG retriever - orchestrates embedding + vector search + citation."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.agent_models import KnowledgeDocument
from app.rag.embeddings import embedding_service
from app.rag.vector_store import VectorStore, VectorEntry, vector_store

logger = get_logger(__name__)


class RAGRetriever:
    def __init__(self, db: AsyncSession | None = None, store: VectorStore | None = None) -> None:
        self._db = db
        self._store = store or vector_store

    async def index_document(
        self,
        source_type: str,
        source_id: str,
        title: str,
        content: str,
        metadata: dict | None = None,
    ) -> str:
        doc_id = str(uuid.uuid4())
        embedding = embedding_service.embed_query(content)
        entry = VectorEntry(
            id=doc_id,
            embedding=embedding,
            content=content,
            source_type=source_type,
            source_id=source_id,
            metadata=metadata or {},
        )
        self._store.add(entry)

        if self._db:
            doc = KnowledgeDocument(
                source_type=source_type,
                source_id=source_id,
                title=title,
                content=content,
                metadata_=metadata,
                embedding_id=doc_id,
                is_indexed=True,
            )
            self._db.add(doc)
            await self._db.flush()

        return doc_id

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        source_types: list[str] | None = None,
    ) -> list[dict]:
        query_embedding = embedding_service.embed_query(query)
        results = self._store.search(query_embedding, top_k=top_k * 2)

        filtered = []
        for entry, score in results:
            if source_types and entry.source_type not in source_types:
                continue
            filtered.append({
                "content": entry.content,
                "source_type": entry.source_type,
                "source_id": entry.source_id,
                "title": entry.metadata.get("title", ""),
                "score": score,
                "metadata": entry.metadata,
            })
            if len(filtered) >= top_k:
                break

        return filtered

    async def build_context(self, query: str, top_k: int = 5) -> str:
        results = await self.retrieve(query, top_k=top_k)
        if not results:
            return ""

        context_parts = []
        for i, r in enumerate(results, 1):
            context_parts.append(
                f"[Source {i}: {r['source_type']} | {r['title']}]\n{r['content']}"
            )
        return "\n\n---\n\n".join(context_parts)

    async def build_citations(self, query: str, top_k: int = 3) -> list[dict]:
        results = await self.retrieve(query, top_k=top_k)
        return [
            {
                "source_type": r["source_type"],
                "source_id": r["source_id"],
                "title": r["title"],
                "excerpt": r["content"][:200],
                "relevance_score": r["score"],
            }
            for r in results
        ]

    async def index_platform_data(self, db: AsyncSession) -> int:
        count = 0
        try:
            from app.domain.models import Job, CandidateProfile, Interview, ScreeningResult

            jobs = (await db.execute(select(Job).where(Job.status == "published"))).scalars().all()
            for job in jobs:
                content = f"Job: {job.title} at {job.company}. {job.description[:500]}"
                await self.index_document("job", str(job.id), job.title, content, {"company": job.company})
                count += 1

            profiles = (await db.execute(select(CandidateProfile))).scalars().all()
            for p in profiles:
                content = f"Candidate profile. Current role: {p.current_role or 'N/A'}. Location: {p.location or 'N/A'}. Bio: {p.bio or 'N/A'}"
                await self.index_document("candidate", str(p.id), f"Candidate {str(p.id)[:8]}", content)
                count += 1

            interviews = (await db.execute(select(Interview))).scalars().all()
            for iv in interviews:
                content = f"Interview for job {str(iv.job_id)[:8]}. Type: {iv.interview_type}. Status: {iv.status}."
                await self.index_document("interview", str(iv.id), f"Interview {str(iv.id)[:8]}", content)
                count += 1
        except Exception as exc:
            logger.warning("Platform data indexing partial failure: %s", exc)

        return count


rag_retriever = RAGRetriever()
