"""
Query router: decide, per question, which retrieval mode to run.

Routes among the routable modes (vector, graph, hybrid) following the project design:
  * vector  — single-hop, detail/factoid questions.
  * graph   — multi-hop, comparison, relationship, corpus-wide ("global") questions.
  * hybrid  — the "always run both" fused path; the router's fallback when it is unsure.

Levels (chosen with --router):
  * none    — no routing (the runner uses the --modes list as before).
  * rules   — R1: keyword/pattern rules. Offline, zero model cost.
  * llm     — R3: one LLM call classifies the question type, mapped to a mode.
  * oracle  — post-hoc upper bound; computed in the report from per-mode scores, not here.

Only ``rules`` and ``llm`` make a live decision in this module. ``oracle`` is handled by
the report (it needs the measured scores of every mode), and ``none`` is handled by the
runner.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Phrases that strongly suggest multi-hop / comparison / relational / global questions,
# which favour the graph (or fused) path.
_GRAPH_CUES = [
    r"\bcompare\b", r"\bcomparison\b", r"\bdifference between\b", r"\bversus\b", r"\bvs\.?\b",
    r"\bboth\b", r"\brelationship\b", r"\brelated\b", r"\bconnection\b", r"\bconnect(ed|s)?\b",
    r"\boverall\b", r"\bacross\b", r"\bmain themes?\b", r"\bsummar(y|ise|ize)\b",
    r"\bhow many\b", r"\bwhich .* and .*\b", r"\bwho .* and .*\b",
]

# Cues that suggest a simple single-hop factoid (favour vector).
_VECTOR_CUES = [
    r"^what is\b", r"^what are\b", r"^who is\b", r"^when (did|was|is)\b",
    r"^where (is|was)\b", r"\bdefine\b", r"\bdefinition of\b",
]


def _count_capitalized_entities(question: str) -> int:
    """Rough proxy for number of named entities (capitalized tokens after the first word)."""
    tokens = question.split()
    return sum(1 for t in tokens[1:] if t[:1].isupper())


def route_rules(question: str) -> str:
    """R1 rule-based routing. Returns 'vector', 'graph', or 'hybrid'."""
    q = question.lower().strip()

    graph_hit = any(re.search(p, q) for p in _GRAPH_CUES)
    vector_hit = any(re.search(p, q) for p in _VECTOR_CUES)
    many_entities = _count_capitalized_entities(question) >= 2

    # Explicit comparison/relational cue is the strongest signal -> graph.
    if graph_hit:
        return "graph"
    # A clear single-hop definitional/factoid pattern -> vector, even if it names an
    # entity (e.g. "What is Regulation T?"). Checked before the entity-count heuristic.
    if vector_hit:
        return "vector"
    # Several named entities with no factoid cue suggests a multi-entity/bridge question.
    if many_entities:
        return "graph"
    # Unsure -> run both (fused). Safe default: best accuracy, higher cost.
    return "hybrid"


_LLM_ROUTER_PROMPT = """Classify the question into exactly one category:

- FACT: a single-hop factual lookup answerable from one passage.
- MULTIHOP: needs chaining facts across multiple passages.
- COMPARISON: compares two or more entities.
- GLOBAL: broad, thematic, or corpus-wide ("overall", "main themes").

Question: {question}

Reply with ONLY one word: FACT, MULTIHOP, COMPARISON, or GLOBAL.
Category:"""

_CATEGORY_TO_MODE = {
    "FACT": "vector",
    "MULTIHOP": "graph",
    "COMPARISON": "graph",
    "GLOBAL": "hybrid",
}

_router_agent_cache = {}


async def route_llm(question: str, router_model: str) -> str:
    """R3 LLM-based routing. One short classification call. Falls back to rules on failure."""
    try:
        from pydantic_ai import Agent

        from agent.providers import get_llm_model

        agent = _router_agent_cache.get(router_model)
        if agent is None:
            agent = Agent(
                get_llm_model(router_model),
                system_prompt="You are a precise query classifier.",
            )
            _router_agent_cache[router_model] = agent

        result = await agent.run(_LLM_ROUTER_PROMPT.format(question=question))
        raw = str(getattr(result, "output", "") or "").upper()
        for cat, mode in _CATEGORY_TO_MODE.items():
            if cat in raw:
                return mode
        # Unparseable -> fall back to rules.
        return route_rules(question)
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM router failed (%s); falling back to rules.", exc)
        return route_rules(question)


async def choose_mode(router: str, question: str, router_model: Optional[str]) -> str:
    """Pick a routable mode for a question given the router level."""
    if router == "rules":
        return route_rules(question)
    if router == "llm":
        model = router_model or "mistral"
        return await route_llm(question, model)
    # 'none'/'oracle' do not make a live per-question choice here.
    return "hybrid"
