"""
Golden-standard scoring for generated answers.

Each evaluation question carries a reference ("golden") answer and an optional list of
``must_include`` keywords. This module scores an LLM's generated answer against that
reference using three complementary, dependency-light signals, plus an overall composite:

1. **Token-overlap F1** — word-level precision/recall F1 between the answer and the golden
   reference (after normalization). Rewards saying the right things without padding.
2. **Keyword coverage** — fraction of ``must_include`` phrases present in the answer.
   Directly checks that specific required facts (numbers, rule names) appear.
3. **Embedding similarity** — cosine similarity between the answer and the golden reference
   embeddings. Rewards semantic equivalence even when wording differs. Uses the project's
   existing embedding client; skipped gracefully if unavailable.

The composite ``overall_score`` is a weighted blend of whichever signals are available.

An optional **LLM-judge** (``llm_judge_score``) asks a model to grade the answer 1-5 against
the golden reference and is only run when explicitly requested.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Composite weights (only applied over the signals that are actually available).
WEIGHT_F1 = 0.35
WEIGHT_KEYWORD = 0.35
WEIGHT_EMBEDDING = 0.30


@dataclass
class ScoreResult:
    f1: Optional[float] = None
    keyword_coverage: Optional[float] = None
    embedding_similarity: Optional[float] = None
    overall_score: Optional[float] = None
    llm_judge_score: Optional[float] = None  # normalized 0-1 (from a 1-5 grade)
    missing_keywords: List[str] = field(default_factory=list)

    def as_row(self) -> Dict[str, object]:
        def fmt(x):
            return "" if x is None else round(x, 4)

        return {
            "score_f1": fmt(self.f1),
            "score_keyword_coverage": fmt(self.keyword_coverage),
            "score_embedding_similarity": fmt(self.embedding_similarity),
            "score_overall": fmt(self.overall_score),
            "score_llm_judge": fmt(self.llm_judge_score),
            "missing_keywords": "; ".join(self.missing_keywords),
        }


_WORD_RE = re.compile(r"[a-z0-9]+")
# Common words ignored for F1 so scoring focuses on content words.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are", "be",
    "that", "this", "it", "as", "at", "by", "with", "from", "must", "may", "any",
    "each", "which", "under", "within", "its", "their", "they", "them", "has", "have",
}


def _normalize(text: str) -> List[str]:
    tokens = _WORD_RE.findall((text or "").lower())
    return [t for t in tokens if t not in _STOPWORDS]


def token_f1(answer: str, reference: str) -> float:
    """Word-level F1 between answer and reference (content words only)."""
    a = _normalize(answer)
    r = _normalize(reference)
    if not a or not r:
        return 0.0
    from collections import Counter

    a_counts, r_counts = Counter(a), Counter(r)
    overlap = sum((a_counts & r_counts).values())
    if overlap == 0:
        return 0.0
    precision = overlap / len(a)
    recall = overlap / len(r)
    return 2 * precision * recall / (precision + recall)


def keyword_coverage(answer: str, keywords: List[str]) -> "tuple[Optional[float], List[str]]":
    """Fraction of required keywords/phrases present in the answer (case-insensitive)."""
    if not keywords:
        return None, []
    lower = (answer or "").lower()
    missing = [k for k in keywords if k.lower() not in lower]
    covered = len(keywords) - len(missing)
    return covered / len(keywords), missing


def _cosine(a: List[float], b: List[float]) -> float:
    import math

    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    val = dot / (na * nb)
    return max(0.0, min(1.0, val))


async def embedding_similarity(answer: str, reference: str) -> Optional[float]:
    """Cosine similarity of answer vs reference embeddings. None if embedding fails."""
    if not answer or not reference:
        return 0.0
    try:
        from agent.tools import generate_embedding

        a_emb = await generate_embedding(answer)
        r_emb = await generate_embedding(reference)
        return _cosine(a_emb, r_emb)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Embedding similarity unavailable: %s", exc)
        return None


def _composite(f1, kw, emb) -> Optional[float]:
    parts = []
    if f1 is not None:
        parts.append((WEIGHT_F1, f1))
    if kw is not None:
        parts.append((WEIGHT_KEYWORD, kw))
    if emb is not None:
        parts.append((WEIGHT_EMBEDDING, emb))
    if not parts:
        return None
    total_w = sum(w for w, _ in parts)
    return sum(w * v for w, v in parts) / total_w


async def score_answer(
    answer: str,
    reference: Optional[str],
    must_include: Optional[List[str]] = None,
    use_embedding: bool = True,
) -> ScoreResult:
    """
    Score one generated answer against its golden reference.

    If there is no reference and no keywords, returns an empty ScoreResult (nothing to
    score against).
    """
    must_include = must_include or []
    if not reference and not must_include:
        return ScoreResult()

    f1 = token_f1(answer, reference) if reference else None
    kw, missing = keyword_coverage(answer, must_include)
    emb = None
    if use_embedding and reference:
        emb = await embedding_similarity(answer, reference)

    overall = _composite(f1, kw, emb)
    return ScoreResult(
        f1=f1,
        keyword_coverage=kw,
        embedding_similarity=emb,
        overall_score=overall,
        missing_keywords=missing,
    )


# ----- Optional LLM-as-judge --------------------------------------------------------------

_JUDGE_PROMPT = """You are grading an answer against a reference (golden) answer.

Question: {question}

Reference answer: {reference}

Candidate answer: {answer}

Grade how well the candidate answer matches the reference on factual correctness and
completeness. Reply with ONLY a single integer from 1 to 5, where:
5 = fully correct and complete
4 = mostly correct, minor omission
3 = partially correct
2 = largely incorrect
1 = incorrect or irrelevant
Score:"""


async def llm_judge(
    question: str, answer: str, reference: str, judge_model: str
) -> Optional[float]:
    """Ask an LLM to grade the answer 1-5 against the reference; return normalized 0-1."""
    if not reference or not answer:
        return None
    try:
        from pydantic_ai import Agent

        from agent.providers import get_llm_model

        agent = Agent(get_llm_model(judge_model), system_prompt="You are a strict grader.")
        prompt = _JUDGE_PROMPT.format(
            question=question, reference=reference, answer=answer
        )
        result = await agent.run(prompt)
        raw = str(getattr(result, "output", "") or getattr(result, "data", ""))
        match = re.search(r"[1-5]", raw)
        if not match:
            return None
        grade = int(match.group(0))
        return (grade - 1) / 4.0  # map 1..5 -> 0..1
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM judge failed: %s", exc)
        return None
