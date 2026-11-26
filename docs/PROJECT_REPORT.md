# Project Report: Vector-DB and LLM Benchmarking Extension for Graph-RAG

## 1. Summary

This project extends an existing Graph-RAG system (PostgreSQL+pgvector for vector search,
Neo4j for a knowledge graph, local Ollama LLMs) with two capabilities:

1. A **swappable vector-store layer** that lets the same embedded chunks be queried against
   three vector databases — PostgreSQL+pgvector (default), Qdrant (embedded), and ChromaDB
   (persistent local) — through one common interface, with no change to default behavior.
2. A **benchmark harness** that runs vector-only, graph-only, and hybrid retrieval across
   each backend and each configured LLM, and records retrieval latency, generation latency,
   token usage, answer text, and golden-standard accuracy scores (token-F1, keyword
   coverage, embedding similarity, optional LLM-judge), plus retrieval recall@k and latency
   percentiles, into a CSV and a Markdown report.

A deterministic, offline dataset generator produces a ~1000-document compliance/markets
corpus (111 authored documents that ground the evaluation questions, plus ~889 generated
reference documents) with no network access or paid API keys required.

**Status:** implemented and runnable end to end. A full live benchmark over the 1000-doc
corpus with golden scoring is the remaining step for the user to run on their machine.

## 2. Motivation and goals

The goal was to be able to compare, on one shared set of embedded chunks and one shared set
of evaluation questions:

- **Vector databases** (pgvector vs Qdrant vs ChromaDB) on retrieval quality and latency.
- **Retrieval modes** (vector vs graph vs hybrid).
- **LLMs** (local Ollama models such as mistral and llama3) on answer quality, latency, and
  token usage, given identical retrieved context.

A hard constraint was to preserve all existing functionality — the default pgvector path,
the Neo4j knowledge graph, the API, the CLI — and to keep the whole thing offline and free
to run.

## 3. Architecture

```
                         benchmark/ (runner, scoring, report)
                                    |
             vector / hybrid        |        graph
                                    v
   agent/vector_store/ (BaseVectorStore)      agent/graph_utils.py (Neo4j, unchanged)
     |-- PgVectorStore  (default; wraps existing SQL)
     |-- QdrantStore    (embedded: path or :memory:)
     |-- ChromaStore    (PersistentClient, local dir)
                                    |
                         the selected vector database
                                    |
                 results/comparison_summary.csv + results/golden_report.md
```

### 3.1 Swappable vector store (`agent/vector_store/`)

- `base.py` — `BaseVectorStore` abstract interface plus a fixed result contract
  (`chunk_id, document_id, content, similarity / combined_score / vector_similarity /
  text_similarity, metadata, document_title, document_source`). The contract matches the
  dict shape the existing `agent/db_utils` functions already returned, so downstream code is
  unchanged.
- `pgvector_store.py` — the default backend; its search methods delegate to the existing
  `vector_search` / `hybrid_search` SQL functions, so default behavior is provably identical.
- `qdrant_store.py` — `qdrant-client` in embedded mode (on-disk path or `:memory:`), cosine
  distance; hybrid search blends the vector score with a dependency-free keyword overlap.
- `chroma_store.py` — `chromadb.PersistentClient`, cosine space, same hybrid blend.
- `factory.py` — `create_vector_store(name, ...)` with env defaults (`VECTOR_BACKEND`,
  `QDRANT_PATH`, `CHROMA_PATH`); Qdrant/Chroma are imported lazily so missing optional deps
  only error when that backend is actually selected.

### 3.2 Benchmark harness (`benchmark/`)

- `questions.py` — loads `data/eval_questions.json`; each question has `id`, `question`,
  `expected` (golden reference), `must_include` (required keywords), and a `relevant_source`
  (the corpus file that grounds it, used for recall@k).
- `retrieval.py` — embeds each query once, runs vector/hybrid against a given store and graph
  against the unchanged Neo4j path, measures latency with `perf_counter`, computes recall@k,
  and builds the shared context passed to every LLM.
- `llm_runner.py` — builds each model via the existing OpenAI-compatible provider wiring
  (Ollama `/v1`), runs the same context prompt, captures generation latency and token usage.
- `scoring.py` — token-F1, keyword coverage, embedding similarity, a weighted composite
  (`score_overall`), and an optional LLM-judge (1–5 → 0–1).
- `report.py` — aggregates the per-row CSV into `golden_report.md`: accuracy and latency by
  LLM, by backend, by mode; recall@k and mean rank by backend and by mode; retrieval and
  generation latency percentiles (p50/p95/p99/max); best configuration; worst questions.
- `runner.py` / `__main__.py` — orchestration and CLI.

CLI flags: `--backends`, `--llms`, `--modes`, `--questions`, `--output`, `--limit`,
`--text-weight`, `--load-from-pg`, `--max-questions`, `--judge`, `--no-embedding-score`.

## 4. Dataset

- `data/generate_dataset.py` — 111 authored Markdown documents across nine compliance/markets
  categories (FINRA rules, SEC regulations, FIX protocol, compliance programs, market
  structure, registration/licensing, risk/reporting, clearing/settlement, ethics/conduct).
  These ground the 38 evaluation questions (q1–q38).
- `data/generate_large_corpus.py` — scales to ~1000 documents by generating ~889 distinct
  reference documents (verified unique content) under `data/corpus/10_Scaled_Reference/`,
  leaving the authored documents and golden questions untouched.
- Both are deterministic and fully offline. The scaled directory is gitignored (regenerable).

**Evaluation set:** 38 questions, each with a golden reference answer and required-keyword
list, every keyword verified present in the corpus.

## 5. Metrics

- **Retrieval quality:** `recall@k` (was the known relevant document retrieved in the top-k)
  and mean rank — independent of the LLM, the most direct measure for comparing vector DBs.
- **Answer quality (golden scoring):** token-F1, keyword coverage, embedding similarity, and
  a weighted composite `score_overall`; optional LLM-judge grade.
- **Performance:** retrieval latency and generation latency (ms), reported as averages and as
  p50/p95/p99/max percentiles; token usage per answer.

## 6. Results

### 6.1 Measured run (real)

The only completed live run to date used an earlier corpus (53 documents) and 20 questions,
across all three backends, three modes, and two LLMs (mistral, llama3). Reported figures:

| Dimension | Result |
|---|---|
| Overall accuracy (composite) | 0.539 |
| — token-F1 | 0.338 |
| — keyword coverage | 0.593 |
| — embedding similarity | 0.710 |
| Best config | qdrant + vector + mistral → 0.668 |

By backend (avg overall score / avg retrieval ms):
- qdrant 0.555 / 522 ms, pgvector 0.539 / 807 ms, chroma 0.523 / 671 ms.

By mode: vector 0.579 > hybrid 0.555 > graph 0.483.

By LLM: mistral 0.550 (~24.8 s/gen) vs llama3 0.528 (~26.3 s/gen).

**Interpretation.** The three vector backends scored within a narrow band (0.523–0.555),
which is expected: they hold identical embeddings and all effectively do near-exact search at
this scale, so differences are noise rather than a real ranking. Qdrant showed the lowest
average retrieval latency. Vector and hybrid retrieval beat graph; graph scored lowest and was
slowest, consistent with the knowledge graph being sparsely populated. mistral slightly
outperformed llama3. recall@k and latency-percentile metrics were added after this run and so
are not in these numbers.

### 6.2 1000-document run (pending)

The corpus has since been scaled to 1000 documents and ingested (1000 chunks, graph building
skipped via `--fast`). The full benchmark at this scale, with recall@k and latency
percentiles, is the next run. Because the scaled documents are one chunk each and the backends
share identical vectors, the expectation is that recall@k and accuracy will again be very close
across backends, with latency being the most visible differentiator.

## 7. Limitations (stated plainly)

1. **Scale is too small to rank vector DBs.** At ~1000 chunks, pgvector/Qdrant/Chroma return
   nearly identical results; ANN-index differences only separate at tens of thousands to
   millions of vectors. This project can demonstrate the backends and compare latency, but it
   cannot credibly claim one is more accurate.
2. **Synthetic corpus.** Deterministic templated documents are reproducible but less lexically
   diverse than real-world text, making retrieval easier than in production.
3. **Graph mode underpowered.** Entity extraction depends on a small local model that was not
   always available, so the knowledge graph was often empty and graph-mode results are weak.
4. **LLM judge uses small models.** mistral/llama3 (7–8B) are adequate answer generators for
   factual lookups but weak as judges (noisy grading, self-preference). The deterministic
   metrics (keyword coverage, embedding similarity) and recall@k are more trustworthy here.
5. **No statistical significance.** 38 questions is enough for direction, not for tight
   confidence intervals or small-effect claims.

## 8. Engineering notes / fixes made

- Fixed a pre-existing `hybrid_search` SQL bug (returned `real` where the signature declared
  `double precision`); added `sql/migrations/001_...`.
- Made Neo4j graph search iterate results with `async for` (the async driver requires it).
- Migrated the provider to pydantic-ai v2 (`OpenAIChatModel`).
- Made the graph per-episode timeout configurable (`GRAPH_EPISODE_TIMEOUT`).
- Added a `--fast` ingest path so large corpora load without the graph-extraction stall.

## 9. How to reproduce

```bash
# 1. services + models
docker compose up -d
ollama pull mistral && ollama pull llama3
pip install -r requirements.txt && pip install qdrant-client chromadb

# 2. build + ingest the 1000-doc corpus (fast = skip graph)
python data/generate_dataset.py
python data/generate_large_corpus.py          # -> ~1000 docs
python -m ingestion.ingest --documents ./data/corpus --clean --fast

# 3. sanity benchmark, then full run
python -m benchmark --backends pgvector qdrant chroma --load-from-pg \
  --llms mistral llama3 --modes vector hybrid --max-questions 5 \
  --output results/sanity.csv
python -m benchmark --backends pgvector qdrant chroma --load-from-pg \
  --llms mistral llama3 --modes vector hybrid \
  --output results/comparison_summary.csv

# outputs: results/comparison_summary.csv and results/golden_report.md
```

## 10. Future work (highest value first)

1. **Scale to 10k+ chunks from a real public QA dataset** (e.g. HotpotQA / MS MARCO passages)
   so recall@k can actually distinguish the vector backends. Single biggest upgrade.
2. **Populate the knowledge graph** with an LLM-based entity/relation extractor so graph and
   hybrid modes are meaningful for this domain.
3. **Use a larger judge model** (e.g. a 32B/70B local model) if GPU allows, or drop the judge
   and rely on deterministic metrics + recall@k.
4. **Report confidence** — more questions and repeated runs for variance.

## 11. Conclusion

The project delivers a clean, extensible benchmarking framework: a real swappable vector-store
abstraction with three working backends, a full evaluation harness with golden-standard
scoring and recall@k, a reproducible offline dataset, and honest, measured results at current
scale. Its strength is as engineering and evaluation tooling; its main limitation is dataset
scale, which bounds any claim about which vector database is "best." With a larger, real-text
corpus and a populated graph, the same harness would support genuinely differentiating results.
