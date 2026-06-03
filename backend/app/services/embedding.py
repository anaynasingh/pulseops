"""
PulseOps — Embedding Service
Uses HuggingFace free Inference API for sentence embeddings (384 dims).
Stores and retrieves vector embeddings via pgvector.
"""
import httpx
from uuid import UUID
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, delete
from app.models.models import Embedding
from app.core.config import settings

# HuggingFace free Inference API endpoint
_HF_URL = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{settings.HF_EMBED_MODEL}"


async def get_embedding(text_input: str) -> List[float]:
    """
    Call the HuggingFace free Inference API to get a 384-dim embedding.

    Works without an API key (anonymous, rate-limited) or with HF_API_KEY
    for higher rate limits.  Returns a flat list of floats.
    """
    headers = {"Content-Type": "application/json"}
    if settings.HF_API_KEY:
        headers["Authorization"] = f"Bearer {settings.HF_API_KEY}"

    payload = {"inputs": text_input, "options": {"wait_for_model": True}}

    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        resp = await client.post(_HF_URL, json=payload, headers=headers)
        resp.raise_for_status()
        result = resp.json()

    # HF returns [[vec]] for single-string input or [vec] — normalise to flat list
    if isinstance(result, list) and result and isinstance(result[0], list):
        if result[0] and isinstance(result[0][0], list):
            # Nested mean-pooling fallback: average token vectors
            vectors = result[0]
            dim = len(vectors[0])
            avg = [sum(v[i] for v in vectors) / len(vectors) for i in range(dim)]
            return avg
        return result[0]   # [[0.1, 0.2, ...]] → [0.1, 0.2, ...]
    return result           # [0.1, 0.2, ...] already flat


async def embed_and_store(
    db: AsyncSession,
    content_type: str,
    content_id: UUID,
    text_input: str,
    metadata: Optional[dict] = None,
) -> Embedding:
    """Generate embedding for text and upsert into the embeddings table."""
    vector = await get_embedding(text_input)

    # Delete existing embedding for this content (upsert pattern)
    await db.execute(
        delete(Embedding).where(
            Embedding.content_type == content_type,
            Embedding.content_id == content_id,
        )
    )

    embedding = Embedding(
        content_type=content_type,
        content_id=content_id,
        embedding=vector,
        meta=metadata or {},
    )
    db.add(embedding)
    await db.commit()
    await db.refresh(embedding)
    return embedding


async def embed_and_store_bg(
    content_type: str,
    content_id: UUID,
    text_input: str,
    metadata: Optional[dict] = None,
) -> None:
    """
    Background-task safe version — creates its own DB session.
    Use this when scheduling embed_and_store as a FastAPI BackgroundTask,
    because the request session is already closed when background tasks run.
    """
    import logging
    from app.db.session import AsyncSessionLocal
    logger = logging.getLogger(__name__)
    try:
        async with AsyncSessionLocal() as db:
            await embed_and_store(db, content_type, content_id, text_input, metadata)
    except Exception as exc:
        logger.error(f"embed_and_store_bg failed for {content_type}:{content_id}: {exc}", exc_info=True)


async def semantic_search(
    db: AsyncSession,
    query: str,
    content_types: Optional[List[str]] = None,
    match_threshold: float = 0.65,
    limit: int = 10,
) -> List[dict]:
    """
    Search for semantically similar content using pgvector cosine similarity.
    Returns list of {content_id, content_type, similarity, metadata}.
    """
    query_vector = await get_embedding(query)

    # Build filter clause
    type_filter = ""
    if content_types:
        types_str = ", ".join(f"'{t}'" for t in content_types)
        type_filter = f"AND content_type IN ({types_str})"

    sql = text(f"""
        SELECT
            content_id,
            content_type,
            1 - (embedding <=> CAST(:query_vector AS vector)) AS similarity,
            metadata
        FROM embeddings
        WHERE 1 - (embedding <=> CAST(:query_vector AS vector)) > :threshold
        {type_filter}
        ORDER BY embedding <=> CAST(:query_vector AS vector)
        LIMIT :limit
    """)

    result = await db.execute(
        sql,
        {
            "query_vector": str(query_vector),
            "threshold": match_threshold,
            "limit": limit,
        }
    )

    rows = result.fetchall()
    return [
        {
            "content_id": row.content_id,
            "content_type": row.content_type,
            "similarity": round(float(row.similarity), 4),
            "metadata": row.metadata or {},
        }
        for row in rows
    ]
