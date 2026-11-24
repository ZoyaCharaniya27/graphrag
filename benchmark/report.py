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
        lines.append("\n## Overall accuracy\n")
        lines.append(
            f"- **Average overall score: {_fmt(overall)}**\n"
            f"- Average token-F1: {_fmt(f1)}\n"
            f"- Average keyword coverage: {_fmt(kw)}\n"
            f"- Average embedding similarity: {_fmt(emb)}\n"
        )

    lines.append("\n## By LLM\n")
    lines.append(_group_table(rows, "llm_model"))
    lines.append("\n## By vector backend\n")
    lines.append(_group_table(rows, "backend"))
    lines.append("\n## By retrieval mode\n")
    lines.append(_group_table(rows, "mode"))

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
