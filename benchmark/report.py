"""
Golden-standard summary report.

Aggregates the per-row benchmark results into a readable Markdown report
(``results/golden_report.md`` by default): average accuracy (overall golden score) and
average latency, broken down per LLM, per vector backend, and per retrieval mode, plus the
best-scoring configuration and the lowest-scoring questions.
"""

import os
from collections import defaultdict
from statistics import mean
from typing import Any, Dict, List


def _f(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def _avg(values: List[float]) -> float:
    vals = [v for v in values if v == v]  # drop NaN
    return mean(vals) if vals else float("nan")


def _percentile(values: List[float], pct: float) -> float:
    """Linear-interpolation percentile (pct in [0,100]). NaN if no values."""
    vals = sorted(v for v in values if v == v)
    if not vals:
        return float("nan")
    if len(vals) == 1:
        return vals[0]
    rank = (pct / 100.0) * (len(vals) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(vals) - 1)
    frac = rank - lo
    return vals[lo] + (vals[hi] - vals[lo]) * frac


def _fmt(x: float) -> str:
    return "n/a" if x != x else f"{x:.3f}"


def _fmt_ms(x: float) -> str:
    return "n/a" if x != x else f"{x:.1f}"


def _group_table(rows, key_field, score_field="score_overall") -> str:
    groups: Dict[str, Dict[str, List[float]]] = defaultdict(
        lambda: {"score": [], "ret": [], "gen": [], "n": 0}
    )
    for r in rows:
        if r.get("error"):
            # Still count latency but not score for errored cells.
            pass
        g = groups[str(r.get(key_field, ""))]
        g["score"].append(_f(r.get(score_field)))
        g["ret"].append(_f(r.get("retrieval_latency_ms")))
        g["gen"].append(_f(r.get("generation_latency_ms")))
        g["n"] += 1

    header = (
        f"| {key_field} | rows | avg overall score | avg retrieval ms | avg generation ms |\n"
        "|---|---|---|---|---|\n"
    )
    lines = []
    # Sort by score descending (NaN last).
    def sort_key(item):
        s = _avg(item[1]["score"])
        return (-(s if s == s else -1e9),)

    for name, g in sorted(groups.items(), key=sort_key):
        lines.append(
            f"| {name or '(none)'} | {g['n']} | {_fmt(_avg(g['score']))} "
            f"| {_fmt_ms(_avg(g['ret']))} | {_fmt_ms(_avg(g['gen']))} |"
        )
    return header + "\n".join(lines) + "\n"


def _dedup_retrieval_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One row per (backend, mode, question_id) for retrieval-centric metrics.

    recall@k and retrieval latency are the same across LLMs for a given retrieval, so we
    keep a single representative row to avoid double-counting them by the number of LLMs.
    """
    seen: Dict[tuple, Dict[str, Any]] = {}
    for r in rows:
        key = (r.get("backend"), r.get("mode"), r.get("question_id"))
        if key not in seen:
            seen[key] = r
    return list(seen.values())


def _recall_table(rows, key_field) -> str:
    groups: Dict[str, Dict[str, List[float]]] = defaultdict(
        lambda: {"hit": [], "rank": [], "n": 0}
    )
    for r in rows:
        hit = _f(r.get("recall_at_k"))
        if hit != hit:  # not scored (no labelled relevant source)
            continue
        g = groups[str(r.get(key_field, ""))]
        g["hit"].append(hit)
        rank = _f(r.get("relevant_rank"))
        if rank == rank:
            g["rank"].append(rank)
        g["n"] += 1

    header = (
        f"| {key_field} | scored | recall@k | mean rank (when hit) |\n"
        "|---|---|---|---|\n"
    )
    if not groups:
        return header + "| (no labelled questions) | 0 | n/a | n/a |\n"
    lines = []
    for name, g in sorted(groups.items(), key=lambda kv: -_avg(kv[1]["hit"])):
        lines.append(
            f"| {name or '(none)'} | {g['n']} | {_fmt(_avg(g['hit']))} "
            f"| {_fmt(_avg(g['rank']))} |"
        )
    return header + "\n".join(lines) + "\n"


def _latency_table(rows, key_field) -> str:
    groups: Dict[str, List[float]] = defaultdict(list)
    for r in rows:
        groups[str(r.get(key_field, ""))].append(_f(r.get("retrieval_latency_ms")))
    header = f"| {key_field} | n | p50 | p95 | p99 | max |\n|---|---|---|---|---|---|\n"
    lines = []
    for name, vals in sorted(groups.items(), key=lambda kv: _percentile(kv[1], 50)):
        clean = [v for v in vals if v == v]
        mx = max(clean) if clean else float("nan")
        lines.append(
            f"| {name or '(none)'} | {len(clean)} | {_fmt_ms(_percentile(vals, 50))} "
            f"| {_fmt_ms(_percentile(vals, 95))} | {_fmt_ms(_percentile(vals, 99))} "
            f"| {_fmt_ms(mx)} |"
        )
    return header + "\n".join(lines) + "\n"


def _gen_latency_table(rows, key_field) -> str:
    groups: Dict[str, List[float]] = defaultdict(list)
    for r in rows:
        if r.get("error"):
            continue
        groups[str(r.get(key_field, ""))].append(_f(r.get("generation_latency_ms")))
    header = f"| {key_field} | n | p50 | p95 | p99 | max |\n|---|---|---|---|---|---|\n"
    lines = []
    for name, vals in sorted(groups.items(), key=lambda kv: _percentile(kv[1], 50)):
        clean = [v for v in vals if v == v]
        mx = max(clean) if clean else float("nan")
        lines.append(
            f"| {name or '(none)'} | {len(clean)} | {_fmt_ms(_percentile(vals, 50))} "
            f"| {_fmt_ms(_percentile(vals, 95))} | {_fmt_ms(_percentile(vals, 99))} "
            f"| {_fmt_ms(mx)} |"
        )
    return header + "\n".join(lines) + "\n"


def write_golden_report(rows: List[Dict[str, Any]], config) -> str:
    output_csv = config.output_path
    report_path = os.path.join(
        os.path.dirname(output_csv) or ".", "golden_report.md"
    )

    scored = [r for r in rows if _f(r.get("score_overall")) == _f(r.get("score_overall"))]
    total = len(rows)
    n_scored = len(scored)

    lines: List[str] = []
    lines.append("# Golden-Standard Benchmark Report\n")
    lines.append(
        f"- Backends: {', '.join(config.backends)}\n"
        f"- LLMs: {', '.join(config.llms)}\n"
        f"- Modes: {', '.join(config.modes)}\n"
        f"- Total rows: {total}  |  Scored rows: {n_scored}\n"
        f"- Scoring: token-F1 + keyword coverage + embedding similarity "
        f"(composite = score_overall); LLM judge: "
        f"{config.judge_model or 'disabled'}\n"
    )

    if scored:
        overall = _avg([_f(r.get("score_overall")) for r in scored])
        f1 = _avg([_f(r.get("score_f1")) for r in scored])
        kw = _avg([_f(r.get("score_keyword_coverage")) for r in scored])
        emb = _avg([_f(r.get("score_embedding_similarity")) for r in scored])
        # Overall recall@k across the deduplicated retrievals that were labelled.
        dedup = _dedup_retrieval_rows(rows)
        recall_vals = [
            _f(r.get("recall_at_k"))
            for r in dedup
            if _f(r.get("recall_at_k")) == _f(r.get("recall_at_k"))
        ]
        overall_recall = _avg(recall_vals) if recall_vals else float("nan")
        lines.append("\n## Overall accuracy\n")
        lines.append(
            f"- **Average overall score: {_fmt(overall)}**\n"
            f"- Average token-F1: {_fmt(f1)}\n"
            f"- Average keyword coverage: {_fmt(kw)}\n"
            f"- Average embedding similarity: {_fmt(emb)}\n"
            f"- Overall retrieval recall@k: {_fmt(overall_recall)} "
            f"(over {len(recall_vals)} labelled retrievals)\n"
        )

    lines.append("\n## By LLM\n")
    lines.append(_group_table(rows, "llm_model"))
    lines.append("\n## By vector backend\n")
    lines.append(_group_table(rows, "backend"))
    lines.append("\n## By retrieval mode\n")
    lines.append(_group_table(rows, "mode"))

    # --- Retrieval-quality & latency sections (dedup to one row per backend/mode/question,
    #     since recall and retrieval latency repeat across LLMs for the same retrieval). ---
    retrieval_rows = _dedup_retrieval_rows(rows)
    lines.append("\n## Retrieval quality — recall@k by vector backend\n")
    lines.append(
        "recall@k = fraction of questions whose labelled relevant document was retrieved "
        "in the top-k results (k = the retrieval limit). mean rank = average 1-based "
        "position of that document when retrieved.\n\n"
    )
    lines.append(_recall_table(retrieval_rows, "backend"))
    lines.append("\n## Retrieval quality — recall@k by retrieval mode\n")
    lines.append(_recall_table(retrieval_rows, "mode"))
    lines.append("\n## Retrieval latency percentiles by vector backend (ms)\n")
    lines.append(_latency_table(retrieval_rows, "backend"))
    lines.append("\n## Generation latency percentiles by LLM (ms)\n")
    lines.append(_gen_latency_table(rows, "llm_model"))

    # Best configuration by average overall score.
    combo: Dict[tuple, List[float]] = defaultdict(list)
    for r in scored:
        combo[(r.get("backend"), r.get("mode"), r.get("llm_model"))].append(
            _f(r.get("score_overall"))
        )
    if combo:
        best = max(combo.items(), key=lambda kv: _avg(kv[1]))
        b, m, l = best[0]
        lines.append("\n## Best configuration (by avg overall score)\n")
        lines.append(
            f"- backend=**{b}**, mode=**{m}**, llm=**{l}** -> {_fmt(_avg(best[1]))}\n"
        )

    # Lowest-scoring questions (by min overall score across configs).
    per_q: Dict[str, List[float]] = defaultdict(list)
    q_text: Dict[str, str] = {}
    for r in scored:
        qid = str(r.get("question_id"))
        per_q[qid].append(_f(r.get("score_overall")))
        q_text[qid] = str(r.get("question", ""))
    if per_q:
        worst = sorted(per_q.items(), key=lambda kv: _avg(kv[1]))[:5]
        lines.append("\n## Lowest-scoring questions (avg overall)\n")
        for qid, vals in worst:
            lines.append(f"- `{qid}` ({_fmt(_avg(vals))}): {q_text.get(qid, '')[:100]}\n")

    content = "".join(lines)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)
    return report_path
