"""
Benchmark orchestrator.

For each configured vector backend, each question, each retrieval mode, and each LLM:
  - run retrieval (vector/graph/hybrid) and record latency,
  - pass the SAME retrieved context to every LLM,
  - record generation latency, token usage, and the answer,
  - write one row to results/comparison_summary.csv.

A failure in a single cell is captured in the row's ``error`` column; the run continues.
"""

import csv
import logging
import os
from typing import Any, Dict, List, Optional

from agent.vector_store import create_vector_store
from benchmark import llm_runner, retrieval, router, scoring
from benchmark.config import BenchmarkConfig
from benchmark.questions import EvalQuestion, load_questions
from benchmark.report import write_golden_report

logger = logging.getLogger(__name__)

CSV_FIELDS = [
    "backend",
    "mode",
    "routed_mode",
    "question_id",
    "question",
    "llm_model",
    "retrieval_latency_ms",
    "generation_latency_ms",
    "num_context_chunks",
    "relevant_source",
    "recall_at_k",
    "relevant_rank",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "score_f1",
    "score_keyword_coverage",
    "score_embedding_similarity",
    "score_overall",
    "score_llm_judge",
    "missing_keywords",
    "answer",
    "expected",
    "error",
]


async def _load_from_pg_into(store, dimension: int) -> int:
    """Copy embedded chunks out of pgvector and into ``store`` (for fair comparison)."""
    from agent.vector_store.pgvector_store import PgVectorStore

    source = PgVectorStore(dimension=dimension)
    await source.initialize()
    chunks = await source.iter_all_chunks()
    if not chunks:
        logger.warning("No chunks found in pgvector to load from.")
        return 0

    # Group by document so each document's title/source are attached once.
    by_doc: Dict[str, Dict[str, Any]] = {}
    for c in chunks:
        doc = by_doc.setdefault(
            c["document_id"],
            {
                "title": c.get("document_title") or "",
                "source": c.get("document_source") or "",
                "chunks": [],
            },
        )
        doc["chunks"].append(c)

    total = 0
    for doc_id, doc in by_doc.items():
        total += await store.add_chunks(
            document_id=doc_id,
            title=doc["title"],
            source=doc["source"],
            chunks=doc["chunks"],
        )
    logger.info("Loaded %d chunks into %s from pgvector.", total, store.name)
    return total


async def _run_backend(
    backend: str,
    config: BenchmarkConfig,
    questions: List[EvalQuestion],
    rows: List[Dict[str, Any]],
) -> None:
    logger.info("=== Backend: %s ===", backend)
    store = create_vector_store(backend, dimension=config.dimension)
    await store.initialize()

    try:
        if config.load_from_pg and backend != "pgvector":
            await _load_from_pg_into(store, config.dimension)

        try:
            chunk_count = await store.count()
            logger.info("Backend %s has %d chunks.", backend, chunk_count)
        except Exception:  # noqa: BLE001
            pass

        for q in questions:
            logger.info("[%s] Question %s: %s", backend, q.id, q.question[:80])
            try:
                embedding = await retrieval.embed_query(q.question)
            except Exception as exc:  # noqa: BLE001
                logger.error("Embedding failed for %s: %s", q.id, exc)
                embedding = None

            # With a live router (rules/llm) the router picks ONE mode for this question;
            # otherwise run every configured mode (and oracle is computed later in report).
            routed_mode = ""
            if config.router in ("rules", "llm"):
                routed_mode = await router.choose_mode(
                    config.router, q.question, config.router_model
                )
                # Prominent, easy-to-spot statement of the routing decision.
                logger.info(
                    "ROUTE | %s | router=%s chose mode=%s for: %s",
                    q.id,
                    config.router,
                    routed_mode.upper(),
                    q.question[:70],
                )
                modes_to_run = [routed_mode]
            else:
                modes_to_run = config.modes

            for mode in modes_to_run:
                outcome = await _retrieve(mode, store, embedding, q.question, config)
                context = retrieval.build_context(outcome)
                # recall@k is a property of the retrieval (same for every LLM on this cell)
                recall_hit, recall_rank = retrieval.recall_at_k(
                    outcome, q.relevant_source
                )
                for model_name in config.llms:
                    gen = await llm_runner.generate(q.question, context, model_name)
                    score = await _score(q, gen, config)
                    rows.append(
                        _build_row(
                            backend, mode, q, model_name, outcome, gen, context,
                            score, recall_hit, recall_rank, routed_mode,
                        )
                    )
    finally:
        await store.close()


async def _retrieve(mode, store, embedding, question, config):
    # vector, hybrid (fused), and dense_hybrid all need the query embedding.
    if embedding is None and mode in ("vector", "hybrid", "dense_hybrid"):
        out = retrieval.RetrievalOutcome(mode=mode)
        out.error = "embedding_unavailable"
        return out
    if mode == "vector":
        return await retrieval.run_vector(store, embedding, config.limit)
    if mode == "hybrid":
        # FUSED: always runs both vector and graph, merged with RRF.
        return await retrieval.run_hybrid(
            store, embedding, question, config.limit, config.text_weight
        )
    if mode == "dense_hybrid":
        # Vector store's native dense+keyword blend (no graph).
        return await retrieval.run_dense_hybrid(
            store, embedding, question, config.limit, config.text_weight
        )
    if mode == "graph":
        return await retrieval.run_graph(question, config.limit)
    out = retrieval.RetrievalOutcome(mode=mode)
    out.error = f"unknown_mode:{mode}"
    return out


async def _score(q: EvalQuestion, gen, config: BenchmarkConfig):
    """Score a generated answer against the golden reference. Never raises."""
    if gen.error or not gen.answer:
        return scoring.ScoreResult()
    try:
        result = await scoring.score_answer(
            answer=gen.answer,
            reference=q.expected,
            must_include=q.must_include,
            use_embedding=config.use_embedding_score,
        )
        if config.judge_model and q.expected:
            result.llm_judge_score = await scoring.llm_judge(
                q.question, gen.answer, q.expected, config.judge_model
            )
        return result
    except Exception as exc:  # noqa: BLE001
        logger.warning("Scoring failed for %s: %s", q.id, exc)
        return scoring.ScoreResult()


def _build_row(
    backend, mode, q, model_name, outcome, gen, context, score,
    recall_hit=None, recall_rank=None, routed_mode="",
) -> Dict[str, Any]:
    errors = [e for e in (outcome.error, gen.error) if e]
    row = {
        "backend": backend,
        "mode": mode,
        "routed_mode": routed_mode,
        "question_id": q.id,
        "question": q.question,
        "llm_model": model_name,
        "retrieval_latency_ms": round(outcome.latency_ms, 2),
        "generation_latency_ms": round(gen.generation_latency_ms, 2),
        "num_context_chunks": outcome.num_results,
        "relevant_source": q.relevant_source or "",
        "recall_at_k": "" if recall_hit is None else recall_hit,
        "relevant_rank": "" if recall_rank is None else recall_rank,
        "prompt_tokens": gen.prompt_tokens if gen.prompt_tokens is not None else "",
        "completion_tokens": (
            gen.completion_tokens if gen.completion_tokens is not None else ""
        ),
        "total_tokens": gen.total_tokens if gen.total_tokens is not None else "",
        "answer": (gen.answer or "").replace("\r", " ").replace("\n", " "),
        "expected": (q.expected or "").replace("\r", " ").replace("\n", " "),
        "error": "; ".join(errors),
    }
    row.update(score.as_row())
    return row


def _write_csv(rows: List[Dict[str, Any]], output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        # restval="" fills any columns a partial row omits; extrasaction="ignore"
        # protects against stray keys.
        writer = csv.DictWriter(
            f, fieldnames=CSV_FIELDS, restval="", extrasaction="ignore"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


async def run_benchmark(config: BenchmarkConfig) -> str:
    """Run the full benchmark and write the CSV. Returns the output path."""
    questions = load_questions(config.questions_path)
    if config.max_questions:
        questions = questions[: config.max_questions]

    logger.info(
        "Benchmark: backends=%s llms=%s modes=%s questions=%d",
        config.backends,
        config.llms,
        config.modes,
        len(questions),
    )

    rows: List[Dict[str, Any]] = []
    for backend in config.backends:
        try:
            await _run_backend(backend, config, questions, rows)
        except Exception as exc:  # noqa: BLE001
            logger.error("Backend '%s' failed to run: %s", backend, exc)
            rows.append(
                {
                    "backend": backend,
                    "mode": "",
                    "question_id": "",
                    "question": "",
                    "llm_model": "",
                    "retrieval_latency_ms": "",
                    "generation_latency_ms": "",
                    "num_context_chunks": "",
                    "prompt_tokens": "",
                    "completion_tokens": "",
                    "total_tokens": "",
                    "answer": "",
                    "error": f"backend_init_failed: {exc}",
                }
            )

    _write_csv(rows, config.output_path)
    logger.info("Wrote %d rows to %s", len(rows), config.output_path)

    # Golden-standard summary report alongside the CSV.
    try:
        report_path = write_golden_report(rows, config)
        logger.info("Wrote golden report to %s", report_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to write golden report: %s", exc)

    return config.output_path
