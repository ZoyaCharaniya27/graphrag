#!/usr/bin/env python3
"""
Interactive terminal Q&A over the benchmark stack.

Type a question; this picks a retrieval mode (via the router, or a fixed mode you set),
runs retrieval against the chosen vector backend (+ Neo4j for graph/hybrid), builds the
context, generates an answer with the chosen LLM, and prints:
  * the route taken (which mode, and why if the router chose it),
  * the backend used,
  * retrieval and generation latency,
  * the retrieved sources,
  * the answer.

It reuses the exact benchmark components (router, retrieval, llm_runner, vector stores), so
behavior matches `python -m benchmark`. Requires the same services: Postgres (chunks),
Ollama (LLM), and Neo4j for graph/hybrid.

Usage:
    python -m benchmark.ask                        # defaults: pgvector, router=rules, mistral
    python -m benchmark.ask --backend qdrant --router llm --llm mistral
    python -m benchmark.ask --mode vector          # fixed mode, no router

In-session commands (type at the prompt):
    /backend <pgvector|qdrant|chroma>   switch vector backend
    /router  <none|rules|llm>           set router level (none = use fixed mode)
    /mode    <vector|graph|hybrid|dense_hybrid>   set fixed mode (implies /router none)
    /llm     <model>                    switch answer model
    /limit   <n>                        results per retrieval
    /sources                            toggle printing retrieved sources
    /settings                           show current settings
    /help                               show commands
    /quit                               exit
"""

import argparse
import asyncio
import logging
import time

from agent.vector_store import create_vector_store
from benchmark import llm_runner, retrieval, router

logger = logging.getLogger("benchmark.ask")

ROUTABLE = ("vector", "graph", "hybrid")
ALL_MODES = ("vector", "graph", "hybrid", "dense_hybrid")


class Session:
    def __init__(self, backend, router_level, mode, llm, router_model, limit, show_sources):
        self.backend_name = backend
        self.router_level = router_level      # none | rules | llm
        self.mode = mode                      # fixed mode when router == none
        self.llm = llm
        self.router_model = router_model
        self.limit = limit
        self.show_sources = show_sources
        self.store = None
        self._backend_dim = int(__import__("os").getenv("EMBEDDING_DIMENSION", "384"))

    async def ensure_store(self):
        """(Re)create the vector store if the backend changed."""
        if self.store is not None and getattr(self.store, "name", None) == self.backend_name:
            return
        if self.store is not None:
            try:
                await self.store.close()
            except Exception:  # noqa: BLE001
                pass
        self.store = create_vector_store(self.backend_name, dimension=self._backend_dim)
        await self.store.initialize()

    async def close(self):
        if self.store is not None:
            try:
                await self.store.close()
            except Exception:  # noqa: BLE001
                pass

    def describe(self) -> str:
        routing = (
            f"router={self.router_level}"
            if self.router_level != "none"
            else f"mode={self.mode} (fixed)"
        )
        return (
            f"backend={self.backend_name} | {routing} | llm={self.llm} | "
            f"limit={self.limit} | sources={'on' if self.show_sources else 'off'}"
        )


async def _retrieve(mode, store, embedding, question, limit):
    if mode == "vector":
        return await retrieval.run_vector(store, embedding, limit)
    if mode == "hybrid":
        return await retrieval.run_hybrid(store, embedding, question, limit)
    if mode == "dense_hybrid":
        return await retrieval.run_dense_hybrid(store, embedding, question, limit)
    if mode == "graph":
        return await retrieval.run_graph(question, limit)
    out = retrieval.RetrievalOutcome(mode=mode)
    out.error = f"unknown_mode:{mode}"
    return out


async def answer_once(sess: Session, question: str) -> None:
    await sess.ensure_store()

    # 1) decide the mode
    if sess.router_level in ("rules", "llm"):
        mode = await router.choose_mode(sess.router_level, question, sess.router_model)
        print(f"  ROUTE: router={sess.router_level} chose mode={mode.upper()}")
    else:
        mode = sess.mode
        print(f"  MODE : {mode.upper()} (fixed)")

    # 2) embed (vector/hybrid/dense_hybrid need it)
    embedding = None
    if mode in ("vector", "hybrid", "dense_hybrid"):
        try:
            embedding = await retrieval.embed_query(question)
        except Exception as exc:  # noqa: BLE001
            print(f"  [embedding failed: {exc}]")
            return

    # 3) retrieve
    outcome = await _retrieve(mode, sess.store, embedding, question, sess.limit)
    if outcome.error:
        print(f"  [retrieval note: {outcome.error}]")
    print(
        f"  backend={sess.backend_name} | retrieved {outcome.num_results} items "
        f"in {outcome.latency_ms:.0f} ms"
    )

    if sess.show_sources and outcome.records:
        print("  sources:")
        for i, rec in enumerate(outcome.records[: sess.limit], start=1):
            title = rec.get("document_title") or rec.get("source") or "(untitled)"
            src = rec.get("document_source") or ""
            score = (
                rec.get("similarity")
                or rec.get("combined_score")
                or rec.get("fused_score")
                or ""
            )
            score_str = f" score={float(score):.3f}" if score != "" else ""
            print(f"    [{i}] {title} {src}{score_str}")

    # 4) build context + generate
    context = retrieval.build_context(outcome)
    gen = await llm_runner.generate(question, context, sess.llm)
    if gen.error:
        print(f"  [generation failed: {gen.error}]")
        return

    toks = ""
    if gen.total_tokens is not None:
        toks = f" | tokens={gen.total_tokens}"
    print(f"  llm={sess.llm} | generated in {gen.generation_latency_ms:.0f} ms{toks}")
    print("\n  ANSWER:")
    print("  " + (gen.answer or "").strip().replace("\n", "\n  "))
    print()


def _handle_command(sess: Session, line: str) -> bool:
    """Handle a /command. Returns False to quit, True to continue."""
    parts = line.strip().split()
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if cmd in ("/quit", "/exit", "/q"):
        return False
    if cmd == "/help":
        print(__doc__.split("In-session commands:")[1])
        return True
    if cmd == "/settings":
        print("  " + sess.describe())
        return True
    if cmd == "/backend":
        if arg in ("pgvector", "qdrant", "chroma"):
            sess.backend_name = arg
            print(f"  backend -> {arg} (will connect on next question)")
        else:
            print("  usage: /backend <pgvector|qdrant|chroma>")
        return True
    if cmd == "/router":
        if arg in ("none", "rules", "llm"):
            sess.router_level = arg
            print(f"  router -> {arg}")
        else:
            print("  usage: /router <none|rules|llm>")
        return True
    if cmd == "/mode":
        if arg in ALL_MODES:
            sess.mode = arg
            sess.router_level = "none"
            print(f"  mode -> {arg} (router set to none)")
        else:
            print(f"  usage: /mode <{'|'.join(ALL_MODES)}>")
        return True
    if cmd == "/llm":
        if arg:
            sess.llm = arg
            print(f"  llm -> {arg}")
        else:
            print("  usage: /llm <model>")
        return True
    if cmd == "/limit":
        try:
            sess.limit = max(1, int(arg))
            print(f"  limit -> {sess.limit}")
        except ValueError:
            print("  usage: /limit <n>")
        return True
    if cmd == "/sources":
        sess.show_sources = not sess.show_sources
        print(f"  sources -> {'on' if sess.show_sources else 'off'}")
        return True
    print(f"  unknown command: {cmd} (try /help)")
    return True


async def repl(sess: Session) -> None:
    print("Interactive RAG Q&A. Type a question, or /help for commands, /quit to exit.")
    print("  " + sess.describe())
    print()
    loop = asyncio.get_event_loop()
    while True:
        try:
            line = await loop.run_in_executor(None, input, "ask> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        line = line.strip()
        if not line:
            continue
        if line.startswith("/"):
            if not _handle_command(sess, line):
                break
            continue
        try:
            await answer_once(sess, line)
        except Exception as exc:  # noqa: BLE001
            print(f"  [error: {exc}]")
    await sess.close()
    print("bye.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m benchmark.ask",
        description="Interactive terminal Q&A over the benchmark stack.",
    )
    ap.add_argument("--backend", default="pgvector", choices=["pgvector", "qdrant", "chroma"])
    ap.add_argument("--router", default="rules", choices=["none", "rules", "llm"])
    ap.add_argument(
        "--mode",
        default="hybrid",
        choices=list(ALL_MODES),
        help="Fixed mode used when --router none.",
    )
    ap.add_argument("--llm", default="mistral", help="Answer model (default: mistral).")
    ap.add_argument("--router-model", default="mistral", help="Model for --router llm.")
    ap.add_argument("--limit", type=int, default=5, help="Results per retrieval.")
    ap.add_argument(
        "--no-sources", action="store_true", help="Do not print retrieved sources."
    )
    ap.add_argument("--log-level", default="WARNING", help="Logging level (default WARNING).")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.WARNING),
        format="%(levelname)s %(name)s: %(message)s",
    )

    sess = Session(
        backend=args.backend,
        router_level=args.router,
        mode=args.mode,
        llm=args.llm,
        router_model=args.router_model,
        limit=args.limit,
        show_sources=not args.no_sources,
    )
    asyncio.run(repl(sess))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
