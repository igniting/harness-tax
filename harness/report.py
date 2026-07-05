#!/usr/bin/env python3
"""Aggregate results.jsonl into the tables that test the thesis.

  python3 harness/report.py results/run1.jsonl
"""
import json
import sys
from collections import defaultdict


def main(path):
    rows = [json.loads(l) for l in open(path) if l.strip()]
    by_model = defaultdict(list)
    for r in rows:
        by_model[r["model"]].append(r)

    print(f"{'model':<22} {'n':>3} {'pass@1':>7} {'out_tok/sample':>15} "
          f"{'out_tok/solve':>14} {'cost/solve':>11} {'verbosity':>10}")
    print("-" * 90)
    for model, rs in sorted(by_model.items()):
        n = len(rs)
        solved = [r for r in rs if r["passed"]]
        p1 = len(solved) / n if n else 0
        tok = sum(r["output_tokens"] for r in rs)
        cost = sum(r["cost_usd"] for r in rs)
        tok_per_solve = tok / len(solved) if solved else float("inf")
        cost_per_solve = cost / len(solved) if solved else float("inf")
        # verbosity: chars of non-code prose per sample (should be ~0 given prompt)
        verb = sum(max(0, r["text_chars"] - r["code_chars"]) for r in rs) / n if n else 0
        print(f"{model:<22} {n:>3} {p1:>7.2%} {tok/n:>15.0f} "
              f"{tok_per_solve:>14.0f} {cost_per_solve:>11.4f} {verb:>10.0f}")

    print("\nPer-problem pass@1:")
    probs = sorted({r["problem"] for r in rows})
    models = sorted(by_model)
    header = f"{'problem':<22}" + "".join(f"{m.replace('claude-',''):>16}" for m in models)
    print(header)
    for p in probs:
        line = f"{p:<22}"
        for m in models:
            rs = [r for r in by_model[m] if r["problem"] == p]
            if not rs:
                line += f"{'-':>16}"
            else:
                pr = sum(r["passed"] for r in rs) / len(rs)
                avg_tok = sum(r["output_tokens"] for r in rs) / len(rs)
                line += f"{pr:>7.0%}/{avg_tok:>6.0f}tk"
        print(line)
    print("\n(cell = pass rate / mean output tokens; output tokens include thinking)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/results.jsonl")
