#!/usr/bin/env python3
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
"""
main.py -- Entry point for the HackerRank Orchestrate Support Triage Agent.

Usage:
    python main.py [--input PATH] [--output PATH] [--sample] [--dry-run]

Flags:
    --input   PATH   Override default support_tickets.csv path.
    --output  PATH   Override default output.csv path.
    --sample         Run on sample_support_tickets.csv instead.
    --dry-run        Load corpus + retriever only; don't call API.
"""

import csv
import os
import random
import sys
import argparse
import time
from pathlib import Path

# ── Reproducibility seed (before any imports that use random) ────────────────
random.seed(42)

# ── Project-level imports ─────────────────────────────────────────────────────
from config import (
    ANTHROPIC_API_KEY, GEMINI_API_KEY, INPUT_CSV, OUTPUT_CSV,
    TICKETS_DIR, RANDOM_SEED,
)
from corpus_loader import load_corpus
from retriever import BM25Retriever
from agent import SupportTriageAgent

OUTPUT_FIELDS = ["status", "product_area", "response", "justification", "request_type"]

BANNER = """
==========================================================
   HackerRank Orchestrate - Support Triage Agent v1.0
   Multi-domain: HackerRank | Claude | Visa
==========================================================
"""


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Support Triage Agent")
    parser.add_argument("--input",  default=str(INPUT_CSV),  help="Path to input CSV")
    parser.add_argument("--output", default=str(OUTPUT_CSV), help="Path to output CSV")
    parser.add_argument("--sample", action="store_true",
                        help="Use sample_support_tickets.csv")
    parser.add_argument("--dry-run", action="store_true",
                        help="Load corpus only; skip API calls")
    return parser.parse_args()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_tickets(path: str) -> list:
    if not os.path.exists(path):
        print(f"[error] Input file not found: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        # Normalize column names (strip whitespace, lowercase for matching)
        rows = []
        for row in reader:
            normalized = {}
            for k, v in row.items():
                clean_key = k.strip().lower()
                # Map to expected keys
                if clean_key in ("issue",):
                    normalized["issue"] = v
                elif clean_key in ("subject",):
                    normalized["subject"] = v
                elif clean_key in ("company",):
                    normalized["company"] = v
                else:
                    normalized[clean_key] = v
            rows.append(normalized)
        return rows


def _write_output(path: str, rows: list):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _print_summary(results: list):
    total = len(results)
    statuses = [r["status"] for r in results]
    types    = [r["request_type"] for r in results]
    print(f"\n{'-'*56}")
    print(f"  Total processed : {total}")
    print(f"  replied         : {statuses.count('replied')}")
    print(f"  escalated       : {statuses.count('escalated')}")
    print(f"  product_issue   : {types.count('product_issue')}")
    print(f"  feature_request : {types.count('feature_request')}")
    print(f"  bug             : {types.count('bug')}")
    print(f"  invalid         : {types.count('invalid')}")
    print(f"{'-'*56}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(BANNER)
    args = parse_args()

    # Resolve paths
    input_path  = args.input
    output_path = args.output

    if args.sample:
        input_path  = str(Path(TICKETS_DIR) / "sample_support_tickets.csv")
        output_path = str(Path(TICKETS_DIR) / "sample_output.csv")
        print(f"[mode] SAMPLE run: {input_path}")

    if args.dry_run:
        print("[mode] DRY-RUN -- API calls skipped.\n")

    # -- Validate API key --
    if not args.dry_run and not ANTHROPIC_API_KEY and not GEMINI_API_KEY:
        print("[error] No API key set. Set one of:")
        print("        GEMINI_API_KEY   (free at https://aistudio.google.com/apikey)")
        print("        ANTHROPIC_API_KEY (paid)")
        sys.exit(1)

    # ── Step 1: Load corpus ───────────────────────────────────────────────────
    print("[1/4] Loading support corpus ...")
    t0 = time.time()
    documents = load_corpus()
    if not documents:
        print("[error] No documents loaded. Check the data/ directory.")
        sys.exit(1)
    print(f"      -> {len(documents)} chunks loaded in {time.time()-t0:.1f}s")

    # ── Step 2: Build BM25 index ──────────────────────────────────────────────
    print("[2/4] Building BM25 retrieval index ...")
    t0 = time.time()
    retriever = BM25Retriever(documents)
    print(f"      -> index ready in {time.time()-t0:.1f}s")

    if args.dry_run:
        # Quick retrieval test
        print("\n[dry-run] Testing retrieval ...")
        test_queries = [
            ("extend test duration", "HackerRank"),
            ("delete conversation", "Claude"),
            ("lost stolen card", "Visa"),
        ]
        for q, c in test_queries:
            results = retriever.retrieve(q, company=c, top_k=3)
            print(f"  Query: '{q}' (company={c})")
            for r in results:
                print(f"    -> [{r['company']}] {r['source']}  score={r['bm25_score']}")
        print("\n[dry-run] Done. Exiting before API calls.")
        return

    # ── Step 3: Init agent ────────────────────────────────────────────────────
    print("[3/4] Initialising triage agent ...")
    agent = SupportTriageAgent(retriever)
    print("      -> agent ready")

    # ── Step 4: Process tickets ───────────────────────────────────────────────
    print(f"[4/4] Loading tickets from: {input_path}")
    tickets = _load_tickets(input_path)
    print(f"      -> {len(tickets)} tickets found\n")

    results: list = []
    start_time = time.time()

    for i, ticket in enumerate(tickets, 1):
        issue   = ticket.get("issue",   "").strip()
        subject = ticket.get("subject", "").strip()
        company = ticket.get("company", "None").strip()

        preview = (subject or issue)[:65]
        print(f"  [{i:>3}/{len(tickets)}] {preview}")

        result = agent.process(issue, subject, company)
        results.append(result)

        print(f"           status={result['status']:<10} "
              f"type={result['request_type']:<18} "
              f"area={result['product_area'][:30]}")

    elapsed = time.time() - start_time

    # ── Write output ──────────────────────────────────────────────────────────
    _write_output(output_path, results)
    print(f"\n[OK] Output written to: {output_path}")
    print(f"  Processed {len(results)} tickets in {elapsed:.1f}s "
          f"({elapsed/max(len(results),1):.1f}s/ticket)")

    _print_summary(results)


if __name__ == "__main__":
    main()
