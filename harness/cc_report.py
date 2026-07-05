#!/usr/bin/env python3
"""Compare Claude Code harness runs against raw-API runs on the same problems.

  python3 harness/cc_report.py results/cc_results.jsonl [results/results.jsonl]

Prints, per model:
  - pass@1, mean turns, mean output tokens, mean total context tokens
    (input + cache_creation + cache_read), mean reported cost
  - if a raw-API results file is given: harness overhead ratios
    (cc tokens / api tokens for the same model+problem) and pass-rate delta.
And per (agentic, subagents) configuration, so the subagent tax is isolated.
"""
import json
import sys
from collections import defaultdict


def load(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def ctx_total(r):
    return (r.get("input_tokens", 0) + r.get("cache_creation_tokens", 0)
            + r.get("cache_read_tokens", 0))


def main(cc_path, api_path=None):
    cc = load(cc_path)
    groups = defaultdict(list)
    for r in cc:
        groups[(r["model"], r.get("agentic"), r.get("subagents"))].append(r)

    print(f"{'model':<22} {'agentic':>7} {'subag':>6} {'n':>3} {'pass@1':>7} "
          f"{'turns':>6} {'out_tok':>9} {'ctx_tok':>10} {'cost$':>8}")
    print("-" * 88)
    for (model, ag, sub), rs in sorted(groups.items()):
        n = len(rs)
        p1 = sum(r["passed"] for r in rs) / n
        turns = sum(r.get("num_turns") or 0 for r in rs) / n
        out = sum(r["output_tokens"] for r in rs) / n
        ctx = sum(ctx_total(r) for r in rs) / n
        cost = sum(r.get("total_cost_usd") or 0 for r in rs) / n
        print(f"{model:<22} {str(ag):>7} {str(sub):>6} {n:>3} {p1:>7.2%} "
              f"{turns:>6.1f} {out:>9.0f} {ctx:>10.0f} {cost:>8.4f}")

    if api_path:
        api = load(api_path)
        api_by = defaultdict(list)
        for r in api:
            api_by[(r["model"], r["problem"])].append(r)
        print("\nHarness overhead vs raw API (same model+problem, means):")
        print(f"{'model':<22} {'problem':<20} {'out_ratio':>10} {'ctx_ratio':>10} "
              f"{'pass cc/api':>12}")
        print("-" * 78)
        seen = set()
        for r in cc:
            key = (r["model"], r["problem"], r.get("agentic"), r.get("subagents"))
            if key in seen or (r["model"], r["problem"]) not in api_by:
                continue
            seen.add(key)
            cc_rs = [x for x in cc if (x["model"], x["problem"],
                     x.get("agentic"), x.get("subagents")) == key]
            api_rs = api_by[(r["model"], r["problem"])]
            cc_out = sum(x["output_tokens"] for x in cc_rs) / len(cc_rs)
            api_out = sum(x["output_tokens"] for x in api_rs) / len(api_rs)
            cc_ctx = sum(ctx_total(x) for x in cc_rs) / len(cc_rs)
            api_ctx = sum(x["input_tokens"] for x in api_rs) / len(api_rs)
            cc_p = sum(x["passed"] for x in cc_rs) / len(cc_rs)
            api_p = sum(x["passed"] for x in api_rs) / len(api_rs)
            tag = f"{r['model']}[a={r.get('agentic')},s={r.get('subagents')}]"
            print(f"{tag:<22.22} {r['problem']:<20} "
                  f"{cc_out/api_out if api_out else 0:>10.2f} "
                  f"{cc_ctx/api_ctx if api_ctx else 0:>10.2f} "
                  f"{cc_p:>5.0%}/{api_p:<5.0%}")
        print("\nout_ratio  = Claude Code output tokens / raw-API output tokens")
        print("ctx_ratio  = CC (input+cache_creation+cache_read) / raw-API input")
        print("ctx_ratio is the harness tax: system prompt, tool schemas, turn loop,")
        print("cache churn, and (if allowed) subagent fan-out.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/cc_results.jsonl",
         sys.argv[2] if len(sys.argv) > 2 else None)
