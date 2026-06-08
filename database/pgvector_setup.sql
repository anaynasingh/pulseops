-- ============================================================
-- PulseOps — pgvector Extension Setup
-- Run this FIRST before schema.sql
-- ============================================================

-- Enable pgvector extension (requires Supabase or pg with pgvector)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm; -- for fuzzy keyword search

-- ============================================================
-- Embeddings table (central vector store)
-- Stores all embeddings for semantic search + AI memory
-- ============================================================

CREATE TABLE IF NOT EXISTS embeddings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_type    TEXT NOT NULL CHECK (content_type IN (
                        'project', 'task', 'comment', 'meeting',
                        'email', 'summary', 'insight'
                    )),
    content_id      UUID NOT NULL,
    embedding       vector(384) NOT NULL,   -- HuggingFace all-MiniLM-L6-v2 dimensions
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- IVFFlat index for approximate nearest-neighbor search
-- lists=100 is a good default for < 1M rows; tune upward as data grows
CREATE INDEX IF NOT EXISTS idx_embeddings_vector
    ON embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_embeddings_content_type
    ON embeddings (content_type);

CREATE INDEX IF NOT EXISTS idx_embeddings_content_id
    ON embeddings (content_id);

-- ============================================================
-- Helper function: semantic search
-- Returns content_id + similarity score for a given embedding
-- ============================================================

CREATE OR REPLACE FUNCTION semantic_search(
    query_embedding vector(384),
    match_content_types TEXT[] DEFAULT NULL,
    match_threshold FLOAT DEFAULT 0.70,
    match_count INT DEFAULT 20
)
RETURNS TABLE (
    content_id   UUID,
    content_type TEXT,
    similarity   FLOAT,
    metadata     JSONB
)
LANGUAGE sql STABLE
AS $$
    SELECT
        e.content_id,
        e.content_type,
        1 - (e.embedding <=> query_embedding) AS similarity,
        e.metadata
    FROM embeddings e
    WHERE
        (match_content_types IS NULL OR e.content_type = ANY(match_content_types))
        AND 1 - (e.embedding <=> query_embedding) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
$$;
