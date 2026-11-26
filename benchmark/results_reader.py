#!/usr/bin/env python3
"""
Read a benchmark results CSV and pick the winning backend and LLM.

Used by ``benchmark.ask --auto-best`` so the interactive chat is configured with the
combination the benchmark study found best, then routes the retrieval mode per question.

"Best" is deliberately explicit and honest:
  * LLM winner      — highest average ``score_overall`` (answer quality). Ties broken by
                      lower average generation latency.
  * Backend winner  — at this project's scale the backends are typically tied on accuracy
                      (near-identical recall), so the default criterion for the backend is
                      LOWEST average retrieval latency among backends whose accuracy is
                      within a small tolerance of the best. This matches the honest finding
                      "comparable accuracy, choose the fastest". Pass criterion="accuracy"
                      to rank the backend purely by score_overall instead.

Only rows with a numeric ``score_overall`` and no ``error`` are counted.
"""

import csv
from collections import defaultdict
from dataclasses import dataclass
from statistics import mean
from typing import Dict, List, Optional, Tuple


@dataclass
class BestConfig:
    backend: str
    llm: str
    backend_reason: str
    llm_reason: str
    # Per-group stats for transparency / printing.
    backend_stats: Dict[str, Dict[str, float]]
    llm_stats: Dict[str, Dict[str, float]]


def _to_float(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def _avg(vals: List[float]) -> float:
    clean = [v for v in vals if v == v]
    return mean(clean) if clean else float("nan")


def _group_stats(rows, key) -> Dict[str, Dict[str, float]]:
    """Average score / retrieval ms / generation ms per value of ``key``."""
    acc: Dict[str, Dict[str, List[float]]] = defaultdict(
        lambda: {"score": [], "ret": [], "gen": []}
    )
    for r in rows:
        name = r.get(key)
        if not name:
            continue
        acc[name]["score"].append(_to_float(r.get("score_overall")))
        acc[name]["ret"].append(_to_float(r.get("retrieval_latency_ms")))
        acc[name]["gen"].append(_to_float(r.get("generation_latency_ms")))
    out: Dict[str, Dict[str, float]] = {}
    for name, d in acc.items():
        out[name] = {
            "score": _avg(d["score"]),
            "ret": _avg(d["ret"]),
            "gen": _avg(d["gen"]),
        }
    return out


def load_rows(csv_path: str) -> List[dict]:
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    # Keep only scored, non-errored rows.
    keep = []
    for r in rows:
        if r.get("error"):
            continue
        if _to_float(r.get("score_overall")) != _to_float(r.get("score_overall")):
            continue
        keep.append(r)
    return keep


def pick_best(
    csv_path: str,
    backend_criterion: str = "latency",
    accuracy_tolerance: float = 0.02,
) -> BestConfig:
    """
    Choose the best backend and LLM from a results CSV.

    backend_criterion:
      * "latency" (default) — among backends within ``accuracy_tolerance`` of the top
        average score, pick the one with the lowest average retrieval latency.
      * "accuracy" — pick the backend with the highest average score outright.
    """
    rows = load_rows(csv_path)
    if not rows:
        raise ValueError(f"No scored, non-errored rows found in {csv_path}.")

    backend_stats = _group_stats(rows, "backend")
    llm_stats = _group_stats(rows, "llm_model")
    if not backend_stats or not llm_stats:
        raise ValueError(f"{csv_path} is missing backend or llm_model data.")

    # --- LLM winner: highest score, tie-break on lower generation latency ---
    def llm_key(item):
        name, s = item
        return (-(s["score"] if s["score"] == s["score"] else -1e9),
                s["gen"] if s["gen"] == s["gen"] else 1e18)

    best_llm, best_llm_s = sorted(llm_stats.items(), key=llm_key)[0]
    llm_reason = (
        f"highest avg score {best_llm_s['score']:.3f}"
        f" (gen {best_llm_s['gen']:.0f} ms)"
    )

    # --- Backend winner ---
    if backend_criterion == "accuracy":
        best_backend, bs = sorted(
            backend_stats.items(),
            key=lambda it: -(it[1]["score"] if it[1]["score"] == it[1]["score"] else -1e9),
        )[0]
        backend_reason = f"highest avg score {bs['score']:.3f}"
    else:
        top_score = max(
            (s["score"] for s in backend_stats.values() if s["score"] == s["score"]),
            default=float("nan"),
        )
        # Candidates within tolerance of the best accuracy.
        candidates = {
            n: s
            for n, s in backend_stats.items()
            if s["score"] == s["score"] and (top_score - s["score"]) <= accuracy_tolerance
        } or backend_stats
        best_backend, bs = sorted(
            candidates.items(),
            key=lambda it: it[1]["ret"] if it[1]["ret"] == it[1]["ret"] else 1e18,
        )[0]
        backend_reason = (
            f"fastest retrieval {bs['ret']:.0f} ms among backends within "
            f"{accuracy_tolerance:.2f} of top accuracy (score {bs['score']:.3f})"
        )

    return BestConfig(
        backend=best_backend,
        llm=best_llm,
        backend_reason=backend_reason,
        llm_reason=llm_reason,
        backend_stats=backend_stats,
        llm_stats=llm_stats,
    )


def format_summary(best: BestConfig) -> str:
    lines = ["Auto-best configuration (from benchmark results):"]
    lines.append(f"  backend = {best.backend}   [{best.backend_reason}]")
    lines.append(f"  llm     = {best.llm}   [{best.llm_reason}]")
    lines.append("  per-backend avg (score / retrieval ms):")
    for n, s in sorted(best.backend_stats.items(), key=lambda it: -it[1]["score"]):
        lines.append(f"    {n:10} {s['score']:.3f} / {s['ret']:.0f} ms")
    lines.append("  per-LLM avg (score / generation ms):")
    for n, s in sorted(best.llm_stats.items(), key=lambda it: -it[1]["score"]):
        lines.append(f"    {n:12} {s['score']:.3f} / {s['gen']:.0f} ms")
    return "\n".join(lines)
