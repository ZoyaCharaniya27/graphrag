# Graph-RAG - Open Source Hybrid Search with Knowledge Graphs

A completely **free and open source** Retrieval-Augmented Generation (RAG) system that combines **Vector Search** (PostgreSQL with pgvector) and **Knowledge Graphs** (Neo4j) for semantic understanding and context-aware question answering.

## 🎯 Key Features

- **100% Open Source**: MIT License, free forever
- **Hybrid Search**: Vector embeddings + knowledge graph traversal
- **Free LLM Models**: Use Ollama locally or any API provider
- **Auto-Ingestion**: Watch directories and automatically process documents
- **Knowledge Extraction**: Extract entities and relationships automatically
- **REST API**: FastAPI-based endpoints for integration
- **CLI Interface**: Interactive command-line chat
- **Docker Ready**: Pre-configured containerized setup

## 📚 Documentation

- **[INSTALLATION.md](INSTALLATION.md)** - Setup and installation guide
- **[docs/BENCHMARK_GUIDE.md](docs/BENCHMARK_GUIDE.md)** - How the vector-DB adapters and the
  multi-LLM benchmark work, end to end

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Optional: Ollama for free local LLM

### 1. Clone and Setup

```bash
git clone https://github.com/EnggTalha/Graph_Rag.git
cd Graph_Rag
```

### 2. Start Docker Services

```bash
docker compose up -d
```

### 3. Install Python Dependencies

```bash
conda create -n graph_rag python=3.11 -y
conda activate graph_rag
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env to set your LLM provider
# Default: uses local Ollama (free, no API key needed)
```

### 5. Initialize Database

```bash
python init_database.py
```

### 6. Start Using

**Interactive CLI:**
```bash
python cli.py
```

**REST API Server:**
```bash
python -m agent.api
# Visit http://localhost:8000/docs for API documentation
```

## 🛠️ Technology Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | FastAPI (Python) |
| **Vector DB** | PostgreSQL + pgvector |
| **Graph DB** | Neo4j |
| **LLM Models** | Ollama (local), OpenAI, Anthropic, HuggingFace |
| **Embeddings** | HuggingFace (free) or OpenAI |
| **Deployment** | Docker & Docker Compose |

## 📁 Project Structure

```
Graph_Rag/
├── agent/              # Core RAG agent and API
│   └── vector_store/   # Swappable vector DB adapters (pgvector/qdrant/chroma)
├── benchmark/          # Vector DB + multi-LLM comparison runner
├── ingestion/          # Document processing pipeline
├── frontend/           # Web interface
├── data/               # Your documents + data/eval_questions.json
├── results/            # Benchmark output (comparison_summary.csv)
├── sql/                # Database schemas
├── docker-compose.yml  # Service configuration
├── cli.py              # Interactive CLI
└── requirements.txt    # Python dependencies
```

## 📖 Common Commands

```bash
# Start services
docker compose up -d

# Ingest documents
python -m ingestion.ingest --documents ./data --watch --verbose

# Start API server
python -m agent.api

# Start CLI
python cli.py

# Run the benchmark (vector DB + LLM comparison -> results/comparison_summary.csv)
python -m benchmark --backends pgvector qdrant chroma --load-from-pg --llms mistral llama3

# View logs
docker compose logs -f

# Stop services
docker compose down
```

## 📊 Benchmarking: Vector DB & Multi-LLM Comparison

The `benchmark/` suite compares vector-DB backends and LLMs over a fixed set of evaluation
questions. It runs **vector-only**, **graph-only**, and **hybrid** retrieval, records
retrieval latency (ms) per vector DB, then passes the **same retrieved context** to each
configured LLM and logs generation latency (ms), token usage, and the answer into
`results/comparison_summary.csv`.

Supported vector backends (swappable via a `BaseVectorStore` interface, pgvector is the
default): **pgvector** (PostgreSQL), **Qdrant** (local path or in-memory), **ChromaDB**
(persistent local directory). Neo4j knowledge-graph retrieval is unchanged.

### Prerequisites

```bash
# Core services + an LLM must be reachable (same as normal usage)
docker compose up -d                      # PostgreSQL (pgvector) + Neo4j
ollama pull mistral                       # at least one LLM (or configure an API in .env)

# Install optional benchmark adapters (only needed for Qdrant/Chroma)
pip install qdrant-client chromadb

# Generate the evaluation corpus, then ingest it
python data/generate_dataset.py                       # authored docs (111) that ground q1-q38
python data/generate_large_corpus.py                  # scale to ~1000 docs (offline, no API key)
python -m ingestion.ingest --documents ./data/corpus  # embed + load into the vector DB
```

`data/generate_large_corpus.py` adds ~900 distinct reference documents under
`data/corpus/10_Scaled_Reference/` so the comparison runs on a realistic volume. It leaves
the 111 authored docs untouched (so q1-q38 stay grounded) and takes `--target N` to change
the total. At 1000 docs expect a longer ingest and a longer benchmark; use `--max-questions`
for quick runs. (With a small corpus the three vector backends return near-identical results;
the larger corpus and the recall@k / latency-percentile metrics below make the comparison
more meaningful, though truly separating ANN backends needs tens of thousands of chunks.)

The corpus (`data/corpus/`) spans nine compliance/markets categories. Ingest it **once**
into pgvector; the benchmark then copies those same chunks into Qdrant/ChromaDB with
`--load-from-pg`. Run ingestion and the benchmark as a **single process** — Qdrant's
embedded on-disk store (`./data/qdrant`) holds a one-process lock, so no API server or
second run may touch that path at the same time. For a large graph build on a slower local
LLM, raise the per-episode timeout with `GRAPH_EPISODE_TIMEOUT` (seconds, default 60), e.g.
`GRAPH_EPISODE_TIMEOUT=120`.

Questions live in `data/eval_questions.json`. Each has a **golden reference answer**
(`expected`) and a `must_include` keyword list, both grounded in the generated corpus, so
answers can be scored for accuracy — not just latency. Edit or replace with your own.

### 1. Vector DB comparison

Run the **same embedded chunks** against each vector DB, one at a time. `--load-from-pg`
copies the chunks already stored in pgvector into Qdrant and ChromaDB so the comparison is
fair (it is a no-op for pgvector):

```bash
python -m benchmark \
  --backends pgvector qdrant chroma \
  --load-from-pg \
  --llms mistral \
  --output results/comparison_summary.csv
```

Each backend contributes rows for every question × mode (`vector`, `graph`, `hybrid`) with
its `retrieval_latency_ms`.

### 2. Multi-LLM comparison

Compare several LLMs on identical retrieved context (local Ollama models and/or
OpenAI-compatible APIs configured in `.env`):

```bash
python -m benchmark \
  --backends pgvector \
  --llms mistral llama3 \
  --output results/comparison_summary.csv
```

### 3. Combined comparison (all backends × all LLMs)

```bash
python -m benchmark \
  --backends pgvector qdrant chroma --load-from-pg \
  --llms mistral llama3 \
  --modes vector graph hybrid \
  --output results/comparison_summary.csv
```

### Output

`results/comparison_summary.csv` columns:

| Column | Meaning |
|--------|---------|
| `backend` | Vector DB used (pgvector / qdrant / chroma) |
| `mode` | Retrieval mode (vector / graph / hybrid) |
| `question_id`, `question` | The evaluation question |
| `llm_model` | LLM that generated the answer |
| `retrieval_latency_ms` | Retrieval time for that backend+mode |
| `generation_latency_ms` | LLM generation time |
| `prompt_tokens`, `completion_tokens`, `total_tokens` | Token usage (blank if unreported) |
| `num_context_chunks` | Chunks included in the shared context |
| `relevant_source` | Known relevant document for the question (for recall@k) |
| `recall_at_k` | 1 if the relevant document was retrieved in the top-k, else 0 (blank if unlabelled) |
| `relevant_rank` | 1-based rank of the relevant document when retrieved |
| `score_f1` | Token-overlap F1 of the answer vs the golden reference |
| `score_keyword_coverage` | Fraction of `must_include` keywords present in the answer |
| `score_embedding_similarity` | Cosine similarity of answer vs golden reference embeddings |
| `score_overall` | Composite accuracy (weighted blend of the three signals above) |
| `score_llm_judge` | Optional LLM grade 0-1 (only with `--judge`) |
| `missing_keywords` | Required keywords the answer omitted |
| `answer` | Generated answer |
| `expected` | Golden reference answer |
| `error` | Any per-cell error (run continues on failure) |

A **golden-standard summary** is also written to `results/golden_report.md`: average accuracy
and latency broken down by LLM, by vector backend, and by retrieval mode; **recall@k** and
mean rank per backend and per mode; **retrieval latency percentiles** (p50/p95/p99/max) per
backend and **generation latency percentiles** per LLM; plus the best-scoring configuration
and the lowest-scoring questions.

**recall@k** measures retrieval quality directly: for each question the relevant source
document is known (from its `relevant_source`, or parsed from the `Grounded in ...` note), and
recall@k is the fraction of questions whose relevant document appears in the top-k retrieved
results. This is the metric that actually distinguishes vector backends, independent of the
LLM. The CSV adds `relevant_source`, `recall_at_k`, and `relevant_rank` columns.

### Golden-standard accuracy scoring

Every generated answer is scored against the question's golden reference using three
complementary signals, combined into `score_overall`:

- **Token-F1** — word-level overlap with the reference (right content, no padding).
- **Keyword coverage** — did the answer include the required facts (`must_include`)?
- **Embedding similarity** — semantic closeness to the reference (handles paraphrasing).

Optional, slower, more realistic: add `--judge mistral` (or any model) to also have an LLM
grade each answer 1-5 against the reference (`score_llm_judge`). Use `--no-embedding-score`
to skip the embedding signal for faster, fully offline scoring.

### Useful flags

```bash
python -m benchmark --help
#   --backends {pgvector,qdrant,chroma} ...
#   --llms MODEL [MODEL ...]
#   --modes {vector,graph,hybrid} ...
#   --questions PATH        (default: data/eval_questions.json)
#   --output PATH           (default: results/comparison_summary.csv)
#   --limit N               (max results per retrieval, default 5)
#   --text-weight FLOAT     (hybrid text weight 0-1, default 0.3)
#   --load-from-pg          (copy pgvector chunks into the selected backend)
#   --max-questions N       (quick run on first N questions)
#   --judge MODEL           (also grade answers 1-5 with an LLM judge)
#   --no-embedding-score    (skip embedding-similarity scoring)
```

Relevant `.env` settings: `VECTOR_BACKEND`, `EMBEDDING_DIMENSION`, `QDRANT_PATH`,
`QDRANT_IN_MEMORY`, `CHROMA_PATH`, `BENCHMARK_LLMS`, `BENCHMARK_LIMIT` (see `.env.example`).

### Troubleshooting

**`hybrid_search` error: "Returned type real does not match expected type double
precision in column 6"** — the original `hybrid_search` SQL function returned `real` from
`ts_rank_cd` while declaring `double precision`. This is fixed in `sql/schema.sql`. Apply it
to an existing database with either:

```bash
python init_database.py
# or just the targeted migration:
psql "$DATABASE_URL" -f sql/migrations/001_fix_hybrid_search_float_type.sql
```

**Graph mode returns 0 results / Neo4j warns `label Episode does not exist`** — the
knowledge graph has not been populated yet. Graph retrieval reads `Episode` nodes created
during ingestion. Run ingestion with graph building enabled (the default) so episodes exist:

```bash
python -m ingestion.ingest --documents ./data
```

An empty graph is not an error; the benchmark records 0 graph results and continues.

## 🤖 Using Free Local Models (Ollama)

No API keys needed! Run everything on your machine:

```bash
# Install Ollama from https://ollama.ai

# Download a free model
ollama pull mistral

# In .env, set:
LLM_PROVIDER=ollama
LLM_MODEL=mistral

# Start using
python cli.py
```

## 💰 Using Commercial APIs (Optional)

If you prefer paid providers with more powerful models:

```bash
# In .env, set:
LLM_PROVIDER=openai
LLM_API_KEY=sk-proj-your-key-here
```

Supported providers:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- HuggingFace (free cloud models)
- Any OpenAI-compatible API

## 📋 Supported File Formats

- **Text**: `.txt`, `.md`, `.markdown`, `.rst`
- **Documents**: `.pdf`, `.doc`, `.docx`
- **Data**: `.json`, `.csv`, `.xlsx`
- **Code**: `.py`, `.js`, `.ts`, etc.

## 🔗 API Documentation

Once API server is running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🐛 Troubleshooting

**Docker services won't start:**
```bash
# Check if ports are in use
lsof -i :5432    # PostgreSQL
lsof -i :7687    # Neo4j
lsof -i :6379    # Redis

# View logs
docker compose logs
```

**Import errors:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

**Database connection issues:**
```bash
# Check database is initialized
python init_database.py

# View database logs
docker compose logs postgres
```

## 📞 Support

For issues and questions:
- Check [INSTALLATION.md](INSTALLATION.md) for detailed setup
- Review docker compose logs: `docker compose logs`
- Check .env configuration

## 📄 License

MIT License - See LICENSE file for details

## 🎉 Getting Started

See [INSTALLATION.md](INSTALLATION.md) for complete setup instructions for all platforms (Linux, macOS, Windows, WSL2).

---

Built with ❤️ using FastAPI, PostgreSQL, Neo4j, and Ollama.
