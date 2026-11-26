-- Migration 001: fix hybrid_search return-type mismatch
--
-- The original hybrid_search() declares combined_score / vector_similarity /
-- text_similarity as FLOAT (double precision), but ts_rank_cd() returns `real`
-- (single precision). That makes column 6 (text_similarity) and column 4
-- (combined_score) come back as `real`, so PostgreSQL raises:
--   "structure of query does not match function result type
--    DETAIL: Returned type real does not match expected type double precision in column 6."
--
-- Fix: cast the score expressions to double precision so the returned columns
-- match the declared signature. Results are unchanged (only the numeric type).
--
-- Apply to a running database with:
--   psql "$DATABASE_URL" -f sql/migrations/001_fix_hybrid_search_float_type.sql
-- or re-run: python init_database.py   (schema.sql already contains this fix)

CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding vector(384),
    query_text TEXT,
    match_count INT DEFAULT 10,
    text_weight FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    combined_score FLOAT,
    vector_similarity FLOAT,
    text_similarity FLOAT,
    metadata JSONB,
    document_title TEXT,
    document_source TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH vector_results AS (
        SELECT
            c.id AS chunk_id,
            c.document_id,
            c.content,
            1 - (c.embedding <=> query_embedding) AS vector_sim,
            c.metadata,
            d.title AS doc_title,
            d.source AS doc_source
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.embedding IS NOT NULL
    ),
    text_results AS (
        SELECT
            c.id AS chunk_id,
            c.document_id,
            c.content,
            ts_rank_cd(to_tsvector('english', c.content), plainto_tsquery('english', query_text))::double precision AS text_sim,
            c.metadata,
            d.title AS doc_title,
            d.source AS doc_source
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE to_tsvector('english', c.content) @@ plainto_tsquery('english', query_text)
    )
    SELECT
        COALESCE(v.chunk_id, t.chunk_id) AS chunk_id,
        COALESCE(v.document_id, t.document_id) AS document_id,
        COALESCE(v.content, t.content) AS content,
        (COALESCE(v.vector_sim, 0) * (1 - text_weight) + COALESCE(t.text_sim, 0) * text_weight)::double precision AS combined_score,
        COALESCE(v.vector_sim, 0)::double precision AS vector_similarity,
        COALESCE(t.text_sim, 0)::double precision AS text_similarity,
        COALESCE(v.metadata, t.metadata) AS metadata,
        COALESCE(v.doc_title, t.doc_title) AS document_title,
        COALESCE(v.doc_source, t.doc_source) AS document_source
    FROM vector_results v
    FULL OUTER JOIN text_results t ON v.chunk_id = t.chunk_id
    ORDER BY combined_score DESC
    LIMIT match_count;
END;
$$;
