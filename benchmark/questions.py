"""Load and normalize evaluation questions from a JSON file."""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

DEFAULT_QUESTIONS_PATH = os.path.join("data", "eval_questions.json")


@dataclass
class EvalQuestion:
    id: str
    question: str
    expected: Optional[str] = None
    notes: Optional[str] = None
    must_include: list = field(default_factory=list)
    # Relative path of the corpus file that grounds the answer, used for recall@k.
    # Taken from an explicit "relevant_source" key, else parsed from the notes string.
    relevant_source: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


def _parse_relevant_source(item: Dict[str, Any]) -> Optional[str]:
    """Resolve the grounding corpus path for recall@k scoring.

    Prefers an explicit ``relevant_source`` field; otherwise parses the common
    ``"Grounded in <path>"`` convention used in the ``notes`` field.
    """
    explicit = item.get("relevant_source")
    if explicit:
        return str(explicit).strip()
    notes = item.get("notes") or ""
    marker = "Grounded in "
    if marker in notes:
        return notes.split(marker, 1)[1].strip().rstrip(".")
    return None


def load_questions(path: str = DEFAULT_QUESTIONS_PATH) -> List[EvalQuestion]:
    """
    Load questions from a JSON file.

    The file must contain a JSON list. Each item is either a string (treated as the
    question text) or an object with at least a ``question`` field and optional ``id``,
    ``expected`` and ``notes`` fields. Unknown fields are preserved in ``extra``.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Evaluation questions file not found: {path}. "
            "Create it or pass --questions with a valid path."
        )

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON list of questions.")

    questions: List[EvalQuestion] = []
    for idx, item in enumerate(data):
        if isinstance(item, str):
            questions.append(EvalQuestion(id=f"q{idx + 1}", question=item))
            continue
        if not isinstance(item, dict):
            raise ValueError(
                f"Question #{idx + 1} in {path} must be a string or object."
            )
        text = item.get("question")
        if not text:
            raise ValueError(f"Question #{idx + 1} in {path} is missing 'question'.")
        known = {"id", "question", "expected", "notes", "must_include", "relevant_source"}
        extra = {k: v for k, v in item.items() if k not in known}
        must_include = item.get("must_include") or []
        if not isinstance(must_include, list):
            must_include = [must_include]
        questions.append(
            EvalQuestion(
                id=str(item.get("id") or f"q{idx + 1}"),
                question=text,
                expected=item.get("expected"),
                notes=item.get("notes"),
                must_include=[str(k) for k in must_include],
                relevant_source=_parse_relevant_source(item),
                extra=extra,
            )
        )

    if not questions:
        raise ValueError(f"No questions found in {path}.")
    return questions
