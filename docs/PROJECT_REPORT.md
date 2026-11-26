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

**Status:** implemented and runnable end to end, including the knowledge graph (the entity
extraction model must be pulled; ingestion run without `--fast` now populates Neo4j and
graph/hybrid retrieval return real results). Vector-DB, LLM, and retrieval-mode comparisons are
summarized in §6; the full 1000-doc run to refresh those tables is the remaining step for the
user to run on their machine.

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

### 4a. Real public dataset (HotpotQA)

To move beyond the synthetic corpus, `data/load_real_dataset.py` loads a configurable slice of
**HotpotQA** (via the `datasets` library; a one-time download, no paid API key). HotpotQA was
chosen because each question ships with its **gold supporting paragraphs**, which map directly
onto this project's `relevant_source` → recall@k machinery: the loader writes each question's
gold passage into the corpus and records it as that question's `relevant_source`, so recall@k
measures whether a backend retrieved the *truly* relevant document rather than a synthetic
stand-in. Passages are written to `data/corpus_real/` and the golden set to
`data/eval_questions_real.json` (same schema the benchmark already parses); the synthetic corpus
and q1–q38 are untouched, and both real artifacts are gitignored (regenerable). This is the
integration that makes the vector-DB comparison genuinely differentiating, since the text is
diverse real-world prose and relevance is labelled. (Scale is still bounded by how large a slice
is downloaded; tens of thousands of chunks is where ANN backends separate most clearly.)

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

### 6.2 1000-document run (in progress)

The corpus has been scaled to 1000 documents and ingested (1000 chunks). The full benchmark at
this scale, with recall@k and latency percentiles, is the run to populate the comparison
tables in §6.3–§6.5 below. Because the scaled documents are one chunk each and the backends
share identical vectors, the expectation is that recall@k and accuracy will be very close
across backends, with **latency** the most visible differentiator; the larger corpus mainly
sharpens the latency and recall signals relative to the 53-doc run.

### 6.2a Knowledge graph status (now populated)

Earlier runs left the Neo4j graph empty because entity extraction called an Ollama model
(`qwen3:0.6b` by default, overridable via `LLM_CHOICE`) that was not pulled, so every
extraction returned HTTP 404 and timed out — graph mode therefore returned no results. After
pulling the extraction model, graph building succeeds: extraction calls return HTTP 200 and
episodes are created (a harmless first-attempt retry occurs while the small model cold-loads
into GPU memory, after which it is warm). Graph building is enabled by running ingestion
**without** `--fast`; a configurable `GRAPH_EPISODE_TIMEOUT` (default 60s) governs the
per-episode budget. With the graph populated, graph-only and hybrid retrieval now return real
results rather than empty sets, so the three-mode comparison below is meaningful.

Trade-off: graph building makes one extraction LLM call per chunk, so ingesting 1000 docs with
the graph on is substantially slower than the `--fast` (vector-only) path and is best run on
the GPU (Tesla) host.

### 6.3 Vector database comparison (pgvector vs Qdrant vs ChromaDB)

All three backends store the identical 384-dim embeddings and are queried through the same
`BaseVectorStore` interface, so this comparison isolates the database, not the embedding.

| Vector DB | Mode / deployment | Index | Avg retrieval latency (53-doc run) | Notes |
|---|---|---|---|---|
| PostgreSQL + pgvector | server (Docker) | IVFFlat (cosine) | ~807 ms | Default; reuses existing SQL and pool. |
| Qdrant | embedded, local path / `:memory:` | HNSW (cosine) | ~522 ms (fastest) | No server; single-process lock on the on-disk path. |
| ChromaDB | embedded, persistent local dir | HNSW (cosine) | ~671 ms | No server; metadata flattened to scalars. |

Observed accuracy (composite `score_overall`, 53-doc run): qdrant 0.555, pgvector 0.539,
chroma 0.523 — a 0.03 spread, i.e. within measurement noise. **Honest reading:** at this scale
the backends are statistically indistinguishable on accuracy because they return essentially
the same nearest neighbours; the only robust differentiator observed was **latency**, where
Qdrant's embedded HNSW was fastest and pgvector slowest. recall@k (added after the 53-doc run)
is the metric that will best separate them and is reported per backend in `golden_report.md`
once the 1000-doc run completes.

Qualitative differences that matter in practice (independent of these numbers):

| Aspect | pgvector | Qdrant | ChromaDB |
|---|---|---|---|
| Needs a running server | Yes (Postgres) | No (embedded) | No (embedded) |
| Native full-text / hybrid | Yes (SQL `ts_rank`) | Client-side blend here | Client-side blend here |
| Operational familiarity | High (just SQL) | Medium | Medium |
| Concurrency | Pooled connections | Single-process on-disk lock | Single process |
| Best fit | Already on Postgres | Fast local experiments | Simple local persistence |

### 6.4 LLM comparison (mistral vs llama3, and API models)

Each LLM answers from the **same retrieved context**, so this isolates the model.

| LLM | Host | Avg answer quality (53-doc run) | Avg generation latency | Token usage |
|---|---|---|---|---|
| mistral (7B) | local Ollama | 0.550 | ~24.8 s | recorded per row |
| llama3 (8B) | local Ollama | 0.528 | ~26.3 s | recorded per row |

**Honest reading:** mistral edged llama3 by ~0.02 — again within noise for 20 questions, so
this is a directional observation, not a ranking. Both are adequate *answer* generators for
factual lookups over retrieved text, but weak as *judges*. Generation latency on CPU/small GPU
is tens of seconds per answer; a Tesla GPU reduces this substantially.

The harness also supports OpenAI-compatible **API models** (set the base URL + API key; pass
e.g. `--llms gpt-4o-mini`), which is the recommended path for a **stronger judge**
(`--judge gpt-4o-mini` / a larger local model). Embeddings and the vector DBs remain local; only
the LLM call is remote. This mixes a cheap local answer model with a high-quality remote judge.

### 6.5 Retrieval mode comparison (vector vs graph vs hybrid)

| Mode | What it queries | Avg accuracy (53-doc run) | Avg retrieval latency | Status |
|---|---|---|---|---|
| vector | vector DB only | 0.579 (best) | ~102 ms | Strong for factual lookups. |
| hybrid | vector + keyword blend | 0.555 | ~148 ms | Close to vector here. |
| graph | Neo4j knowledge graph | 0.483 (lowest) | ~1751 ms (slowest) | Was empty in the 53-doc run; now populated (§6.2a). |

**Honest reading:** vector retrieval was both the most accurate and the fastest for this
factual-lookup question set; hybrid was comparable; graph was lowest and slowest. Crucially,
the 53-doc graph numbers reflect an **empty** graph. Now that extraction works and the graph is
populated, the graph/hybrid numbers should be re-measured — graph may still trail vector for
pure factual lookups (its strength is relationship/multi-hop queries, which this question set
does not emphasize), but it will no longer be empty.

## 7. Limitations (stated plainly)

1. **Scale is too small to rank vector DBs.** At ~1000 chunks, pgvector/Qdrant/Chroma return
   nearly identical results; ANN-index differences only separate at tens of thousands to
   millions of vectors. This project can demonstrate the backends and compare latency, but it
   cannot credibly claim one is more accurate.
2. **Synthetic corpus.** Deterministic templated documents are reproducible but less lexically
   diverse than real-world text, making retrieval easier than in production.
3. **Graph mode: now populated but still lookup-limited.** The earlier empty-graph problem is
   fixed (the extraction model must be pulled, and ingestion run without `--fast`). However,
   extraction still uses a small model and the evaluation questions are factual lookups, which
   vector search already serves well; graph's advantage is relationship/multi-hop queries that
   this question set does not emphasize. A stronger LLM-based extractor and multi-hop questions
   would let graph mode show its strength. Graph ingestion is also much slower (one LLM call
   per chunk), so large-corpus graph builds should run on the GPU host.
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

Common setup (both corpora):

```bash
docker compose up -d
ollama pull mistral && ollama pull llama3 && ollama pull qwen3:0.6b   # last = graph extractor
pip install -r requirements.txt && pip install qdrant-client chromadb
# keep the small extractor warm to avoid cold-start retries during graph ingest:
#   set OLLAMA_KEEP_ALIVE=30m in the Ollama server environment
```

### 9.1 Synthetic corpus run

```bash
# build the ~1000-doc synthetic corpus
python data/generate_dataset.py
python data/generate_large_corpus.py                       # -> data/corpus/ (~1000 docs)

# ingest (drop --fast to build the knowledge graph; add it to skip the graph and go fast)
export GRAPH_EPISODE_TIMEOUT=120
python -m ingestion.ingest --documents ./data/corpus --clean

# benchmark (defaults to data/eval_questions.json = q1-q38)
python -m benchmark --backends pgvector qdrant chroma --load-from-pg \
  --llms mistral llama3 --modes vector graph hybrid \
  --output results/synthetic.csv
# -> results/synthetic.csv + results/golden_report.md
```

### 9.2 Real dataset run (HotpotQA)

```bash
pip install datasets                                        # one-time download, no paid key

# build the real corpus + golden questions with labelled gold passages
python data/load_real_dataset.py --num-questions 100 --max-docs 2000
#   -> data/corpus_real/  and  data/eval_questions_real.json

# ingest the REAL corpus folder
export GRAPH_EPISODE_TIMEOUT=120
python -m ingestion.ingest --documents ./data/corpus_real --clean

# benchmark the REAL question set (note --questions and a distinct --output)
python -m benchmark --backends pgvector qdrant chroma --load-from-pg \
  --llms mistral llama3 --modes vector graph hybrid \
  --questions data/eval_questions_real.json \
  --output results/real.csv
# -> results/real.csv + results/golden_report.md
```

### 9.3 What differs between the two runs

Only the corpus build, the ingest `--documents` path, and the benchmark `--questions`
/ `--output` differ; all other flags behave identically.

| Step | Synthetic | Real (HotpotQA) |
|---|---|---|
| Build corpus | `generate_dataset.py` + `generate_large_corpus.py` | `load_real_dataset.py` (needs `datasets`) |
| Ingest `--documents` | `./data/corpus` | `./data/corpus_real` |
| Benchmark `--questions` | *(omit → defaults to `data/eval_questions.json`, q1–q38)* | `--questions data/eval_questions_real.json` (r1, r2, …) |
| Questions / answers | hand-authored compliance Q&A | real HotpotQA questions + gold answers |
| `relevant_source` for recall@k | the synthetic `.md` that grounds the answer | the HotpotQA gold supporting passage |
| `--output` | `results/synthetic.csv` | `results/real.csv` |

Notes: use a distinct `--output` per run so one run's CSV/`golden_report.md` does not overwrite
the other; add `--fast` to either ingest to skip the graph (faster, graph mode returns empty);
add `--judge <model>` to either benchmark to enable LLM-judge scoring.

## 10. Future work (highest value first)

1. **Real public dataset — implemented (HotpotQA), now scale it up.** `data/load_real_dataset.py`
   loads HotpotQA with labelled gold passages for recall@k (see §4a). The remaining step is to
   run it at larger `--num-questions` / `--max-docs` (toward 10k+ chunks), where ANN backends
   separate most clearly, and record the results. This is the single biggest upgrade in
   credibility for the vector-DB comparison.
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
