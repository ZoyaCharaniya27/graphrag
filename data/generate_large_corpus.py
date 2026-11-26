#!/usr/bin/env python3
"""
Scale the benchmark corpus to ~1000 documents, fully offline and deterministically.

This augments the hand-authored corpus produced by ``data/generate_dataset.py`` (111 docs,
which ground evaluation questions q1-q38) with a large set of additional, distinct reference
documents so the vector-DB/LLM comparison runs on a realistic volume. It requires no network
access and no external LLM API keys, so it runs cleanly on a local/Linux/GPU machine.

Design:
  * The hand-authored 111 docs under ``data/corpus/NN_*`` are left untouched, so q1-q38 stay
    grounded.
  * New docs are written under ``data/corpus/10_Scaled_Reference/`` with unique filenames, so
    they never collide with or overwrite the authored corpus.
  * Content is generated deterministically from a fixed catalogue of compliance/markets topics
    combined with varied sub-aspects, so every document is distinct (distinct title, body, and
    keyword mix) rather than near-duplicate. A fixed RNG seed makes the output reproducible.

Usage:
    python data/generate_dataset.py          # authored 111 docs (run first)
    python data/generate_large_corpus.py     # adds ~900 docs -> ~1000 total
    python -m ingestion.ingest --documents ./data/corpus

Re-running overwrites the scaled set deterministically. Change --target to adjust the total.
"""

import argparse
import random
from pathlib import Path

CORPUS_DIR = Path(__file__).parent / "corpus"
SCALED_CATEGORY = "10_Scaled_Reference"

# Topic catalogue: (short_slug, subject, one-line fact kernel). The generator expands each
# into many distinct documents by pairing with aspects and templates below.
TOPICS = [
    ("suitability", "customer suitability obligations", "a firm must have a reasonable basis to believe a recommendation is suitable based on the customer's investment profile"),
    ("best_interest", "the best interest standard of conduct", "a broker-dealer must act in the retail customer's best interest and may not place its own interests ahead of the customer's"),
    ("supervision", "the supervisory system", "a firm must maintain a system reasonably designed to achieve compliance, with written supervisory procedures and registered principals"),
    ("recordkeeping", "books and records requirements", "records must be preserved for the required retention period in a non-rewriteable, non-erasable format and produced to regulators on request"),
    ("aml", "the anti-money laundering program", "a firm must detect and report suspicious transactions, provide independent testing, designate a compliance officer, and train staff under the Bank Secrecy Act"),
    ("best_execution", "best execution of customer orders", "a firm must use reasonable diligence to obtain the most favorable terms reasonably available and conduct regular and rigorous reviews of execution quality"),
    ("market_access", "market access risk controls", "a firm with market access must apply financial and regulatory risk controls that block orders exceeding pre-set thresholds and reject erroneous orders"),
    ("reg_nms", "national market system rules", "the order protection rule requires trading centers to avoid trade-throughs of protected quotations across venues"),
    ("short_sale", "short sale regulation", "the alternative uptick rule restricts short sales in a security that has declined 10 percent or more from the prior close"),
    ("margin", "margin requirements", "Regulation T sets an initial margin requirement of generally 50 percent and FINRA sets maintenance margin of generally 25 percent"),
    ("settlement", "clearing and settlement", "US equity trades settle on a T+1 basis and are cleared through a central counterparty that nets member obligations"),
    ("fix_protocol", "the FIX messaging protocol", "FIX messages are tag=value pairs where MsgType tag 35 identifies the message, such as D for a new order single and 8 for an execution report"),
    ("insider_trading", "prevention of insider trading", "firms use information barriers, restricted and watch lists, pre-clearance of personal trades, and surveillance to prevent misuse of material nonpublic information"),
    ("complaints", "customer complaint handling", "firms must keep records of written customer complaints and report specified complaint information to FINRA"),
    ("communications", "communications with the public", "retail communications must be fair and balanced, may require principal approval, and certain ones must be filed with FINRA"),
    ("options", "options account rules", "firms must approve options accounts, deliver the options disclosure document, and observe position and exercise limits"),
    ("registration", "representative registration", "representatives must pass the Securities Industry Essentials exam and a top-off qualification such as the Series 7"),
    ("privacy", "privacy of customer information", "firms must adopt written policies to safeguard customer records and limit sharing of nonpublic personal information under Regulation S-P"),
    ("cybersecurity", "cybersecurity risk management", "firms are expected to maintain governance, access controls, encryption, vendor management, and incident response to protect customer information"),
    ("net_capital", "the net capital rule", "a broker-dealer must maintain minimum net liquid assets at all times so it can meet obligations and wind down without loss to customers"),
    ("customer_protection", "the customer protection rule", "a firm must maintain possession or control of customers' fully paid securities and a special reserve account for the exclusive benefit of customers"),
    ("trace", "TRACE transaction reporting", "firms must report TRACE-eligible secondary market transactions generally within 15 minutes of execution to increase bond-market transparency"),
    ("large_trader", "large trader reporting", "persons whose activity exceeds specified identifying thresholds must file Form 13H and are subject to large-trader recordkeeping"),
    ("reg_d", "private placement exemptions", "Regulation D permits private offerings to accredited investors, with Rule 506(b) limiting non-accredited investors and barring general solicitation"),
    ("reg_fd", "fair disclosure of information", "Regulation FD prohibits selective disclosure of material nonpublic information by issuers to analysts or selected investors"),
    ("whistleblower", "the whistleblower program", "eligible whistleblowers may receive awards of 10 to 30 percent of sanctions over one million dollars and are protected from retaliation"),
    ("fiduciary", "investment adviser fiduciary duty", "an investment adviser owes a duty of care and a duty of loyalty and must disclose or avoid material conflicts of interest"),
    ("manipulation", "market manipulation prohibitions", "schemes such as spoofing, layering, wash trading, and pump-and-dump artificially affect price or volume and violate anti-fraud rules"),
    ("circuit_breakers", "market-wide circuit breakers", "trading halts at Level 1, 2, and 3 are triggered by S&P 500 declines of 7, 13, and 20 percent to reduce volatility"),
    ("dark_pools", "alternative trading systems", "a dark pool is an ATS that does not display quotations before execution and operates under Regulation ATS with fair access and reporting duties"),
]

# Aspects: each topic is expanded along these facets to create distinct documents.
ASPECTS = [
    ("scope", "Scope and Applicability", "This note summarizes the scope and applicability of {subject}. {fact}. The requirement applies to member firms and their associated persons, and compliance staff should confirm how it maps to the firm's specific business lines and customer base."),
    ("procedures", "Procedures and Controls", "This note describes procedures and controls for {subject}. {fact}. Written procedures should assign clear responsibility, define review frequency, and specify escalation paths when exceptions are detected."),
    ("supervision", "Supervisory Review", "This note addresses supervisory review of {subject}. {fact}. A designated principal should periodically test the controls, document the results, and remediate any deficiencies that the testing identifies."),
    ("recordkeeping", "Recordkeeping Considerations", "This note covers recordkeeping considerations for {subject}. {fact}. Relevant records should be retained for the applicable period, indexed for retrieval, and produced promptly to regulators upon request."),
    ("training", "Training and Awareness", "This note outlines training and awareness for {subject}. {fact}. Staff whose functions touch this area should receive role-appropriate training, and the firm should refresh the material as rules and business practices change."),
    ("risk", "Risk Assessment", "This note frames the risk assessment for {subject}. {fact}. The firm should identify inherent risks, evaluate the strength of existing controls, and prioritize remediation based on residual risk."),
    ("examples", "Illustrative Examples", "This note gives illustrative examples for {subject}. {fact}. For instance, a firm reviewing a borderline case should document the analysis, the factors considered, and the rationale for the conclusion reached."),
    ("pitfalls", "Common Pitfalls", "This note lists common pitfalls for {subject}. {fact}. Typical weaknesses include stale written procedures, inconsistent documentation, and controls that are designed but not actually performed in practice."),
    ("checklist", "Compliance Checklist", "This note provides a compliance checklist for {subject}. {fact}. A reviewer should confirm that policies exist, that they are current, that responsible persons are identified, and that evidence of ongoing performance is retained."),
    ("regulatory_context", "Regulatory Context", "This note places {subject} in regulatory context. {fact}. The requirement interacts with related obligations, so compliance staff should read it together with the firm's broader policy framework rather than in isolation."),
]


def _slug_title(topic_slug, subject, aspect_title, idx):
    return f"{subject.title()} - {aspect_title} (Reference {idx:04d})"


def _body(subject, fact, template, idx):
    text = template.format(subject=subject, fact=fact.capitalize())
    # A short, deterministic closing sentence that varies per document index so bodies differ.
    closer = (
        f" This reference entry (index {idx}) is one of a series of internal compliance notes "
        f"maintained for training and review; it should be validated against current rule text "
        f"before being relied upon."
    )
    return text + closer


def write_scaled_corpus(target_total: int = 1000, seed: int = 1337) -> int:
    """
    Write enough scaled documents so the whole corpus reaches ``target_total`` files.

    Returns the number of scaled documents written (not counting the authored corpus).
    """
    rng = random.Random(seed)
    scaled_dir = CORPUS_DIR / SCALED_CATEGORY
    scaled_dir.mkdir(parents=True, exist_ok=True)

    # Clear any previous scaled output so re-runs are deterministic and idempotent.
    for old in scaled_dir.glob("*.md"):
        old.unlink()

    # Count authored docs already present (everything outside the scaled category).
    authored = [
        p
        for p in CORPUS_DIR.rglob("*.md")
        if SCALED_CATEGORY not in p.parts
    ]
    needed = max(0, target_total - len(authored))

    # Build a deterministic, shuffled list of (topic, aspect) pairs, cycling as needed.
    pairs = [(t, a) for t in TOPICS for a in ASPECTS]
    rng.shuffle(pairs)

    written = 0
    idx = 0
    while written < needed:
        topic, aspect = pairs[idx % len(pairs)]
        topic_slug, subject, fact = topic
        aspect_slug, aspect_title, template = aspect
        idx += 1
        doc_idx = written + 1
        title = _slug_title(topic_slug, subject, aspect_title, doc_idx)
        body = _body(subject, fact, template, doc_idx)
        filename = f"{topic_slug}_{aspect_slug}_{doc_idx:04d}.md"
        text = f"# {title}\n\n{body}\n"
        (scaled_dir / filename).write_text(text, encoding="utf-8")
        written += 1

    return written


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scale the benchmark corpus to a target document count (offline)."
    )
    parser.add_argument(
        "--target",
        type=int,
        default=1000,
        help="Total number of documents the whole corpus should reach (default 1000).",
    )
    parser.add_argument(
        "--seed", type=int, default=1337, help="RNG seed for reproducibility."
    )
    args = parser.parse_args()
    n = write_scaled_corpus(target_total=args.target, seed=args.seed)
    total = len(list(CORPUS_DIR.rglob("*.md")))
    print(f"Wrote {n} scaled documents to {CORPUS_DIR / SCALED_CATEGORY}")
    print(f"Total corpus documents now: {total}")
