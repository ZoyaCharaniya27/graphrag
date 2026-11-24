# Benchmark Extension — How It All Works

This document explains the benchmark extension added to Graph-RAG: what it does, how each
piece fits together, how data flows through it, and how to run and extend it. It assumes no
prior knowledge of the extension and only basic familiarity with Python.

---

## 1. The big picture

Graph-RAG answers questions by retrieving relevant text and feeding it to a language model
(LLM). There are two things you often want to measure and compare:

1. **Which vector database is best?** The system stores text embeddings (numeric
   fingerprints of text) in a *vector database* and searches them by similarity. There are
   several vector databases (PostgreSQL+pgvector, Qdrant, ChromaDB). They differ in speed
   and results.
2. **Which LLM is best?** Given the same retrieved text, different LLMs (mistral, llama3,
   OpenAI models, …) produce different answers at different speeds and token costs.

The benchmark extension lets you measure both, fairly and repeatably, and dumps the numbers
to a CSV you can open in a spreadsheet.

It is built from two independent parts:

- **A swappable vector-store layer** (`agent/vector_store/`) — one common interface with
  three interchangeable backends.
- **A benchmark runner** (`benchmark/`) — a script that loops over backends × questions ×
  retrieval modes × LLMs and records metrics.

Nothing about the existing app behavior changes by default. The knowledge graph (Neo4j)
retrieval path is untouched.

---

## 2. Key concepts (plain definitions)

- **Chunk**: a small slice of a document (e.g. a paragraph). Documents are split into
  chunks so retrieval can return just the relevant parts.
- **Embedding**: a list of numbers (here, 384 of them) that represents the *meaning* of a
  chunk. Similar text → similar numbers. Produced by the model `all-MiniLM-L6-v2`.
- **Vector search**: find the chunks whose embeddings are closest to the question's
  embedding (semantic similarity).
- **Keyword search**: find chunks that literally contain the question's words.
- **Hybrid search**: blend vector and keyword scores into one ranking.
- **Graph search**: look up facts/relationships in the Neo4j knowledge graph instead of
  chunks.
- **Retrieval mode**: which of the three above you use — `vector`, `graph`, or `hybrid`.
- **Vector store / backend / adapter**: the database that holds embeddings and serves
  similarity search. We support `pgvector` (default), `qdrant`, and `chroma`.
- **Latency**: how long something takes, measured here in milliseconds (ms).
- **Token usage**: how many tokens (word-pieces) the LLM read (prompt) and wrote
  (completion). Important for cost and speed comparisons.

---

## 3. Architecture at a glance

```
                      ┌──────────────────────────────────────────────┐
                      │                 benchmark/                     │
                      │                                                │
  data/eval_          │  __main__.py  → parse CLI flags                │
  questions.json ────▶│  config.py    → merge flags + .env             │
                      │  questions.py → load & normalize questions     │
                      │  runner.py    → the orchestration loop         │
                      │     │                                          │
                      │     ├─ retrieval.py → vector / graph / hybrid  │
                      │     │                 + latency (ms)           │
                      │     └─ llm_runner.py → call each LLM on the    │
                      │                        SAME context, capture   │
                      │                        latency + tokens        │
                      └──────────┬───────────────────────┬────────────┘
                                 │                        │
            vector / hybrid      │                        │  graph
                                 ▼                        ▼
             ┌───────────────────────────────┐   ┌──────────────────────┐
             │     agent/vector_store/        │   │  agent/graph_utils.py │
             │  BaseVectorStore (interface)   │   │  Neo4j (UNCHANGED)    │
             │   ├─ PgVectorStore (default)   │   └──────────────────────┘
             │   ├─ QdrantStore               │
             │   └─ ChromaStore               │
             └───────────────────────────────┘
                                 │
                                 ▼
                       the chosen vector DB
                 (Postgres / Qdrant file / Chroma dir)

   Embeddings + results flow out to:  results/comparison_summary.csv
```

---

## 4. The swappable vector-store layer (`agent/vector_store/`)

This is the heart of the "swap the database" feature. Every backend implements the same
interface, so the rest of the code never needs to know which database is behind it.

### 4.1 The interface — `base.py`

`BaseVectorStore` is an abstract class (a contract). Every backend must implement these
async methods:

| Method | What it does |
|--------|--------------|
| `initialize()` | Open connections / create the collection. Safe to call repeatedly. |
| `close()` | Release resources. |
| `add_document(title, source, content, metadata)` | Record a document, return its id. |
| `add_chunks(document_id, title, source, chunks)` | Store chunk embeddings; return count. |
| `vector_search(embedding, limit)` | Pure semantic search. |
| `hybrid_search(embedding, query_text, limit, text_weight)` | Vector + keyword search. |
| `count()` | How many chunks are stored. |
| `clear()` | Delete everything. |

**The result contract.** Every search returns a list of records with the *same keys*, no
matter the backend:

- `vector_search` →
  `chunk_id, document_id, content, similarity, metadata, document_title, document_source`
- `hybrid_search` → those plus `combined_score, vector_similarity, text_similarity`

These exact keys match what the existing `agent/db_utils.py` already returned, which is why
nothing downstream (`agent/tools.py`, the agent, ingestion) had to change.

`base.py` also has small shared helpers:
- `clamp01(x)` — forces a score into the range 0–1.
- `text_overlap_score(query, content)` — a tiny, dependency-free keyword relevance score
  (fraction of query words that appear in the chunk). Used by Qdrant and Chroma to build
  their hybrid score, since those engines don't have Postgres-style full-text ranking.
- `chunk_attr(chunk, name, default)` — reads a field whether a chunk is a dict or an object.

> **Why async?** The rest of the app uses async database drivers. The Qdrant and Chroma
> client libraries are *synchronous*, so their adapters wrap blocking calls in
> `asyncio.to_thread(...)` to stay compatible and non-blocking.

### 4.2 The default backend — `pgvector_store.py`

This wraps the existing PostgreSQL + pgvector setup. Crucially, its search methods simply
**delegate to the unchanged existing functions**:

```python
async def vector_search(self, embedding, limit=10):
    from ..db_utils import vector_search as _vector_search
    return await _vector_search(embedding=embedding, limit=limit)
```

So the default path is provably identical to the original system — the adapter adds no new
behavior, it just presents the same calls behind the common interface. Its write methods
(`add_document`, `add_chunks`) replicate the exact SQL that ingestion already uses.

It also has a bonus method, `iter_all_chunks()`, which reads every stored chunk (including
its embedding) back out of Postgres. The benchmark uses this to copy the *same* chunks into
Qdrant/Chroma for a fair comparison (see §6.2).

### 4.3 Qdrant backend — `qdrant_store.py`

- Uses `qdrant-client` in **embedded mode** (`path=...` for on-disk, or `:memory:`), so no
  separate server is needed.
- Creates a collection sized to the embedding dimension (384) with **cosine** distance.
- Each chunk becomes a "point": the vector plus a payload (content, document id, title,
  source, chunk index, metadata, token count).
- `vector_search` uses Qdrant's native similarity score.
- `hybrid_search` fetches extra candidates, computes `text_overlap_score` for each, then
  blends: `combined = vector*(1-text_weight) + text*text_weight`, and returns the top N.
- Qdrant point ids must be int or UUID, so arbitrary chunk ids are coerced to a UUID via
  `_as_point_id`.

### 4.4 ChromaDB backend — `chroma_store.py`

- Uses `chromadb.PersistentClient(path=...)`, which stores data in a local directory.
- Collection uses cosine space (`{"hnsw:space": "cosine"}`).
- Chroma metadata values must be simple scalars, so nested metadata is JSON-encoded into a
  single `metadata_json` field and decoded on read.
- Chroma returns cosine *distance* (0 = identical). We convert to similarity with
  `1 - distance` (clamped to 0–1).
- `hybrid_search` uses the same blend approach as Qdrant.

### 4.5 Choosing a backend — `factory.py`

```python
from agent.vector_store import create_vector_store
store = create_vector_store("qdrant")   # or "pgvector" / "chroma"
```

- Defaults to the `VECTOR_BACKEND` env var, then `"pgvector"`.
- Reads per-backend settings from the environment: `QDRANT_PATH`, `QDRANT_IN_MEMORY`,
  `CHROMA_PATH`, `EMBEDDING_DIMENSION`.
- **Graceful degradation:** `qdrant-client` and `chromadb` are imported *lazily*, inside the
  branch that needs them. So the core app and the pgvector path work even if those libraries
  aren't installed. You only get an error — a clear, actionable one — if you actually select
  a backend whose library is missing.

---

## 5. The benchmark runner (`benchmark/`)

### 5.1 Questions — `data/eval_questions.json` + `questions.py`

The question set is a JSON list. Each item can be a plain string or an object:

```json
[
  { "id": "q1", "question": "What are the key FINRA rules...", "notes": "optional" },
  "a bare string also works"
]
```

`load_questions()` reads the file and normalizes every item into an `EvalQuestion`
(`id`, `question`, optional `expected`/`notes`). Missing ids are auto-assigned (`q1`, `q2`,
…). Unknown fields are kept in `extra` and otherwise ignored.

### 5.2 Retrieval — `retrieval.py`

- `embed_query(question)` turns the question into a 384-number embedding **once**, reusing
  the app's existing embedding function (`agent.tools.generate_embedding`). The same
  embedding is reused across modes and backends for that question — fair and efficient.
- `run_vector(store, embedding, limit)` and `run_hybrid(...)` call the chosen store.
- `run_graph(query, limit)` calls the **unchanged** Neo4j client
  (`agent.graph_utils.graph_client.search`).
- Each returns a `RetrievalOutcome` with the records, the measured `latency_ms`
  (via `time.perf_counter()`), and an `error` string if it failed.
- `build_context(outcome)` turns the retrieved records into one text block. The *same* block
  is handed to every LLM, so generation comparisons are apples-to-apples.

### 5.3 LLM generation — `llm_runner.py`

- `generate(question, context, model_name)` builds a prompt that embeds the retrieved
  context, then runs the model.
- Models are created with the app's existing wiring (`agent.providers.get_llm_model`), which
  talks to Ollama or any OpenAI-compatible API by base URL + model name. Agents are cached
  per model so they aren't rebuilt every call.
- It records `generation_latency_ms` and extracts **token usage** from the pydantic-ai
  result. `_extract_usage` is deliberately defensive: different library versions name the
  fields differently (`request_tokens`/`input_tokens`/`prompt_tokens`, etc.), so it tries
  several and leaves the value blank if none is reported.
- Any failure is caught and returned in the `error` field instead of crashing the run.

### 5.4 Configuration — `config.py`

`resolve_config(args)` merges command-line flags with `.env` defaults into one
`BenchmarkConfig`:

| Setting | CLI flag | Env fallback | Default |
|---------|----------|--------------|---------|
| backends | `--backends` | `VECTOR_BACKEND` | `pgvector` |
| LLMs | `--llms` | `BENCHMARK_LLMS`, then `LLM_CHOICE` | `mistral` |
| modes | `--modes` | — | `vector graph hybrid` |
| limit | `--limit` | `BENCHMARK_LIMIT` | `5` |
| questions | `--questions` | — | `data/eval_questions.json` |
| output | `--output` | — | `results/comparison_summary.csv` |

### 5.5 Orchestration — `runner.py`

The core loop:

```
for backend in backends:
    store = create_vector_store(backend); initialize()
    (optional) copy chunks from pgvector into this store   # --load-from-pg
    for question in questions:
        embedding = embed(question)
        for mode in modes:                                 # vector / graph / hybrid
            records, retrieval_latency = retrieve(mode, ...)
            context = build_context(records)               # shared across LLMs
            for llm in llms:
                answer, gen_latency, tokens = generate(question, context, llm)
                write one CSV row
    store.close()
write results/comparison_summary.csv
```

**Error isolation:** a failure in a single cell (one question/mode/LLM) is written to that
row's `error` column and the loop continues. A backend that fails to initialize gets a
single error row. The run always produces a CSV.

### 5.6 Entry point — `__main__.py`

Run with `python -m benchmark [flags]`. Use `python -m benchmark --help` to see every flag.

---

## 6. Running it

### 6.1 Prerequisites

```bash
docker compose up -d                 # PostgreSQL (pgvector) + Neo4j
ollama pull mistral                  # at least one LLM, or configure an API in .env
pip install qdrant-client chromadb   # only needed for the Qdrant/Chroma backends
python -m ingestion.ingest --documents ./data   # so the vector DB actually has chunks
```

### 6.2 Vector DB comparison (same chunks across every DB)

```bash
python -m benchmark \
  --backends pgvector qdrant chroma \
  --load-from-pg \
  --llms mistral \
  --output results/comparison_summary.csv
```

`--load-from-pg` copies the chunks already embedded in Postgres into Qdrant and Chroma, so
all three search the identical data. It is a no-op for pgvector itself.

### 6.3 Multi-LLM comparison (same context across every LLM)

```bash
python -m benchmark --backends pgvector --llms mistral llama3
```

### 6.4 Reading the output

`results/comparison_summary.csv` — one row per (backend, mode, question, LLM):

| Column | Meaning |
|--------|---------|
| `backend` | pgvector / qdrant / chroma |
| `mode` | vector / graph / hybrid |
| `question_id`, `question` | the evaluation question |
| `llm_model` | which LLM answered |
| `retrieval_latency_ms` | time to retrieve context for that backend+mode |
| `generation_latency_ms` | time for the LLM to answer |
| `num_context_chunks` | how many chunks were in the shared context |
| `prompt_tokens`, `completion_tokens`, `total_tokens` | token usage (blank if unreported) |
| `answer` | the generated answer (newlines flattened for CSV) |
| `error` | any error for that cell; empty on success |

---

## 6b. Golden-standard scoring (accuracy, not just speed)

Latency and token counts tell you how *cheap/fast* an answer was, not whether it was
*correct*. The golden-standard layer measures correctness by comparing each generated answer
to a known reference ("golden") answer.

### The dataset — `data/generate_dataset.py`

Running `python data/generate_dataset.py` writes ~50 deterministic Markdown documents under
`data/corpus/` across seven compliance/markets categories (FINRA rules, SEC regulations, FIX
protocol, compliance programs, market structure, registration/licensing, risk/reporting).
The content is fixed, so the golden answers can be written against the exact text. Ingest it
with `python -m ingestion.ingest --documents ./data/corpus`.

### The golden questions — `data/eval_questions.json`

Each question now carries two extra fields:

```json
{
  "id": "q2",
  "question": "What are the four component obligations of SEC Regulation Best Interest?",
  "expected": "Reg BI comprises four obligations: the Disclosure Obligation, the Care Obligation, the Conflict of Interest Obligation, and the Compliance Obligation.",
  "must_include": ["Disclosure", "Care", "Conflict of Interest", "Compliance"]
}
```

- `expected` — the golden reference answer.
- `must_include` — specific facts (rule numbers, dollar amounts, named obligations) that a
  correct answer must contain.

### The scorer — `benchmark/scoring.py`

For every generated answer the scorer computes three signals and a composite:

| Signal | Column | What it rewards |
|--------|--------|-----------------|
| Token-overlap F1 | `score_f1` | Using the same content words as the reference (precision + recall). |
| Keyword coverage | `score_keyword_coverage` | Containing the required `must_include` facts. |
| Embedding similarity | `score_embedding_similarity` | Being semantically close even if worded differently. |
| **Composite** | `score_overall` | Weighted blend (0.35 / 0.35 / 0.30) of whatever signals are available. |

Each signal is in the range 0–1. The composite only averages the signals that are actually
available, so disabling embeddings (`--no-embedding-score`) still yields a sensible overall
score from F1 + keywords. The `missing_keywords` column lists any required facts the answer
left out, which is the quickest way to see *why* a model scored low.

**Why three signals instead of one?** Each covers a blind spot of the others. F1 can be
fooled by padding with reference words; keyword coverage can miss paraphrases; embedding
similarity can rate a fluent-but-wrong answer highly. Together they are much harder to game.

### Optional LLM-as-judge

With `--judge <model>`, the scorer additionally asks an LLM to grade each answer 1–5 against
the reference and records it (normalized to 0–1) in `score_llm_judge`. This is slower and
non-deterministic, so it is off by default; the automatic metrics above need no extra LLM
calls.

### The report — `benchmark/report.py`

After the CSV is written, `results/golden_report.md` summarizes accuracy: average
`score_overall` and latency broken down **by LLM**, **by vector backend**, and **by retrieval
mode**, plus the single best-scoring configuration and the five lowest-scoring questions. This
is the "which setup is best" answer at a glance.

---

## 7. The pgvector type fix (why it was needed)

During a live run, hybrid mode failed with:

```
structure of query does not match function result type
DETAIL: Returned type real does not match expected type double precision in column 6.
```

This was a **pre-existing bug** in the `hybrid_search` SQL function (in `sql/schema.sql`),
not in the new code. The function declares its score columns as `FLOAT` (= `double
precision`), but PostgreSQL's `ts_rank_cd()` returns `real` (single precision). That makes
`text_similarity` (column 6) and `combined_score` (column 4) come back as `real`, which
doesn't match the declared signature, so PostgreSQL refuses the result.

The fix casts the score expressions to `double precision`. Apply it to a running database:

```bash
python init_database.py
# or just the targeted migration:
psql "$DATABASE_URL" -f sql/migrations/001_fix_hybrid_search_float_type.sql
```

`match_chunks` (used by plain vector mode) was already correct, which is why vector mode
never errored.

---

## 8. The empty-graph note (not a bug)

If graph mode returns 0 results and Neo4j logs warnings like *"label Episode does not
exist"*, the knowledge graph simply hasn't been populated. Graph retrieval reads `Episode`
nodes that ingestion creates. Run ingestion with graph building enabled (the default):

```bash
python -m ingestion.ingest --documents ./data
```

These Neo4j messages are informational warnings, not errors; the query still runs and
returns an empty list, which the benchmark records and moves on.

---

## 9. What changed vs. what didn't

**Added (new files):**
- `agent/vector_store/` — the interface, three adapters, and the factory.
- `benchmark/` — the runner and its helpers, including `scoring.py` and `report.py`.
- `data/generate_dataset.py` — generates the ~50-document evaluation corpus.
- `data/eval_questions.json` — golden questions with reference answers + required keywords.
- `sql/migrations/001_fix_hybrid_search_float_type.sql` — the type-fix migration.
- `.kiro/specs/vectordb-benchmark/` — the requirements/design/tasks spec.

**Changed (additive only):**
- `sql/schema.sql` — cast fix in `hybrid_search` (results unchanged, only the numeric type).
- `.env.example`, `.gitignore`, `README.md`, `requirements.txt` — new settings/deps/docs.

**Untouched:**
- All existing Python logic in `agent/` and `ingestion/`.
- The Neo4j knowledge-graph retrieval path.
- Default app behavior (pgvector remains the default backend).

---

## 10. Extending it

- **Add a new vector backend:** create `agent/vector_store/yourdb_store.py` subclassing
  `BaseVectorStore`, implement the methods and return the result contract, then add a branch
  in `factory.py`. Nothing else needs to change.
- **Add questions:** edit `data/eval_questions.json`.
- **Add LLMs:** pass more names to `--llms` (they must be reachable via your Ollama /
  OpenAI-compatible configuration).
- **Change what "hybrid" means for Qdrant/Chroma:** adjust `text_overlap_score` in
  `base.py` or the blend in each adapter's `hybrid_search`.
```
