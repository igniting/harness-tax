#!/usr/bin/env python3
"""Grade an artifact-exported microbench_runs.json against the pytest oracles.

  python3 harness/grade_export.py /path/to/microbench_runs.json
"""
import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_tests(problem, code):
    tests = ROOT / "problems" / problem / "tests"
    with tempfile.TemporaryDirectory() as td:
        sol = Path(td) / "solution.py"
        sol.write_text(code)
        env = dict(os.environ)
        env["SOLUTION_PATH"] = str(sol)
        env["PYTHONPATH"] = str(ROOT / "harness")
        try:
            p = subprocess.run(
                [sys.executable, "-m", "pytest", str(tests), "-q"],
                capture_output=True, text=True, timeout=300, env=env, cwd=str(ROOT))
            return p.returncode == 0
        except subprocess.TimeoutExpired:
            return False


def main(path):
    data = json.load(open(path))
    runs = data["runs"] if isinstance(data, dict) else data
    graded = []
    for r in runs:
        if r.get("error"):
            r["passed"], r["grade_note"] = False, "api_error"
        elif r.get("truncated"):
            r["passed"], r["grade_note"] = False, "truncated_excluded"
        elif not r.get("code"):
            r["passed"], r["grade_note"] = False, "no_code_block"
        else:
            r["passed"] = run_tests(r["problem"], r["code"])
            r["grade_note"] = "graded"
        graded.append(r)
        print(f"{r['model']:<24} {r['problem']:<18} s{r.get('sample')} "
              f"-> {'PASS' if r['passed'] else 'fail'} ({r['grade_note']})")

    out = Path(path).with_suffix(".graded.json")
    json.dump(graded, open(out, "w"), indent=1)

    print("\nSummary (truncated runs excluded from denominator):")
    by = defaultdict(list)
    for r in graded:
        if r["grade_note"] in ("graded", "no_code_block"):
            by[r["model"]].append(r)
    print(f"{'model':<24} {'n':>3} {'pass@1':>8} {'out_tok/sample':>15} {'out_tok/solve':>14}")
    for m, rs in sorted(by.items()):
        n = len(rs)
        solved = [r for r in rs if r["passed"]]
        tok = sum(r.get("output_tokens", 0) for r in rs)
        tps = tok / len(solved) if solved else float("inf")
        print(f"{m:<24} {n:>3} {len(solved)/n:>8.2%} {tok/n:>15.0f} {tps:>14.0f}")
    print(f"\nGraded detail written to {out}")


if __name__ == "__main__":
    main(sys.argv[1])
