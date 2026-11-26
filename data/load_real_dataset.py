#!/usr/bin/env python3
"""
Load a REAL public QA/RAG dataset (HotpotQA by default) into the benchmark corpus and build a
matching golden evaluation question set with labelled relevant documents for recall@k.

Why HotpotQA: each question ships with its supporting (gold) context paragraphs, which map
directly onto this project's ``relevant_source`` -> recall@k machinery. That makes the vector-DB
comparison evidence-based (did the backend retrieve the known-relevant passage?) rather than
noise, which the synthetic corpus cannot provide.

This integrates exactly like the synthetic generators:
  * It writes passages as Markdown under ``data/corpus_real/`` (a separate dir, so the authored
    synthetic corpus and q1-q38 are left untouched).
  * It writes ``data/eval_questions_real.json`` using the same question schema the benchmark
    already understands (``id, question, expected, must_include, relevant_source``).
  * You then ingest ``./data/corpus_real`` and benchmark with
    ``--questions data/eval_questions_real.json`` — no CLI flags or schemas change.

Data source (requires a ONE-TIME download; no paid API key):
  * Primary: the Hugging Face ``datasets`` library (``pip install datasets``), dataset
    ``hotpot_qa`` config ``distractor``.
  * The dataset is cached locally after the first download, so subsequent runs are offline.

Usage:
    pip install datasets                     # one-time
    python data/load_real_dataset.py --num-questions 100 --max-docs 5000
    python -m ingestion.ingest --documents ./data/corpus_real --clean --fast
    python -m benchmark --backends pgvector qdrant chroma --load-from-pg \
        --llms mistral llama3 --modes vector hybrid \
        --questions data/eval_questions_real.json --output results/real.csv

Determinism: a fixed --seed makes the sampled slice reproducible.
"""

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).parent
CORPUS_DIR = HERE / "corpus_real"
QUESTIONS_PATH = HERE / "eval_questions_real.json"


def _slug(text: str, maxlen: int = 60) -> str:
    """Filesystem-safe slug from a title string."""
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
    return (s[:maxlen] or "doc").rstrip("_")


def _doc_filename(title: str, idx: int) -> str:
    # Hash keeps filenames unique even when titles repeat or slugify identically.
    h = hashlib.md5(f"{idx}:{title}".encode("utf-8")).hexdigest()[:8]
    return f"{_slug(title)}_{h}.md"


def _write_doc(rel_dir: str, filename: str, title: str, body: str) -> str:
    """Write one Markdown doc; return its path relative to CORPUS_DIR (used as relevant_source)."""
    out_dir = CORPUS_DIR / rel_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    text = f"# {title}\n\n{body.strip()}\n"
    (out_dir / filename).write_text(text, encoding="utf-8")
    return f"{rel_dir}/{filename}"


def _first_keywords(answer: str, k: int = 3):
    """Pick up to k content keywords from the gold answer for the must_include check."""
    stop = {
        "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are",
        "was", "were", "by", "with", "as", "at", "it", "that", "this",
    }
    toks = re.findall(r"[A-Za-z0-9][A-Za-z0-9.\-]+", answer or "")
    kept = [t for t in toks if t.lower() not in stop and len(t) > 2]
    # Preserve order, dedupe.
    seen, out = set(), []
    for t in kept:
        if t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
        if len(out) >= k:
            break
    return out or ([answer.strip()] if answer and answer.strip() else [])


def load_hotpotqa(num_questions: int, seed: int):
    """Load a HotpotQA slice via the datasets library. Returns a list of normalized examples."""
    try:
        from datasets import load_dataset
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "The 'datasets' library is required for the real dataset.\n"
            "Install it with:  pip install datasets\n"
            "(This performs a one-time download of HotpotQA; no paid API key is needed.)"
        ) from exc

    print("Loading HotpotQA (hotpot_qa / distractor, validation split)...")
    ds = load_dataset("hotpot_qa", "distractor", split="validation")
    ds = ds.shuffle(seed=seed).select(range(min(num_questions, len(ds))))

    examples = []
    for row in ds:
        # HotpotQA 'context' is {title: [...], sentences: [[...], ...]}.
        ctx = row.get("context", {})
        titles = ctx.get("title", [])
        sentences = ctx.get("sentences", [])
        paragraphs = {}
        for t, sents in zip(titles, sentences):
            paragraphs[t] = " ".join(s.strip() for s in sents).strip()
        # Supporting facts give the gold (relevant) titles.
        sf = row.get("supporting_facts", {})
        gold_titles = list(dict.fromkeys(sf.get("title", [])))  # unique, ordered
        examples.append(
            {
                "question": (row.get("question") or "").strip(),
                "answer": (row.get("answer") or "").strip(),
                "paragraphs": paragraphs,       # title -> text
                "gold_titles": gold_titles,     # relevant paragraph titles
            }
        )
    return examples


def build(num_questions: int, max_docs: int, seed: int) -> None:
    # Clean previous real corpus/questions so re-runs are deterministic.
    if CORPUS_DIR.exists():
        for p in CORPUS_DIR.rglob("*.md"):
            p.unlink()
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)

    examples = load_hotpotqa(num_questions, seed)

    # Write every unique paragraph once; map title -> relative path for recall@k grounding.
    title_to_source = {}
    doc_count = 0
    for ex in examples:
        for title, body in ex["paragraphs"].items():
            if not body:
                continue
            if title in title_to_source:
                continue
            if max_docs and doc_count >= max_docs:
                continue
            fname = _doc_filename(title, doc_count)
            rel = _write_doc("hotpotqa", fname, title, body)
            title_to_source[title] = rel
            doc_count += 1

    # Build the golden question set. relevant_source = the first gold supporting paragraph
    # that we actually wrote (recall@k is a hit if that document is retrieved).
    questions = []
    used = 0
    for i, ex in enumerate(examples, start=1):
        if not ex["question"] or not ex["answer"]:
            continue
        gold_source = None
        for t in ex["gold_titles"]:
            if t in title_to_source:
                gold_source = title_to_source[t]
                break
        if gold_source is None:
            # No gold paragraph made it into the corpus (e.g. truncated by --max-docs); skip.
            continue
        questions.append(
            {
                "id": f"r{used + 1}",
                "question": ex["question"],
                "expected": ex["answer"],
                "must_include": _first_keywords(ex["answer"], k=3),
                "relevant_source": gold_source,
                "notes": f"HotpotQA validation; gold passage {gold_source}",
            }
        )
        used += 1

    QUESTIONS_PATH.write_text(
        json.dumps(questions, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Wrote {doc_count} documents to {CORPUS_DIR}")
    print(f"Wrote {len(questions)} golden questions to {QUESTIONS_PATH}")
    print("\nNext:")
    print("  python -m ingestion.ingest --documents ./data/corpus_real --clean --fast")
    print(
        "  python -m benchmark --backends pgvector qdrant chroma --load-from-pg "
        "--llms mistral llama3 --modes vector hybrid "
        "--questions data/eval_questions_real.json --output results/real.csv"
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Load a real public QA dataset (HotpotQA) into the benchmark corpus."
    )
    ap.add_argument(
        "--num-questions",
        type=int,
        default=100,
        help="Number of QA examples to sample (default 100). Each contributes its context "
        "paragraphs to the corpus.",
    )
    ap.add_argument(
        "--max-docs",
        type=int,
        default=0,
        help="Cap on total corpus documents written (0 = no cap). Useful to bound ingest time.",
    )
    ap.add_argument("--seed", type=int, default=1337, help="Sampling seed (reproducible).")
    args = ap.parse_args()
    build(args.num_questions, args.max_docs, args.seed)
