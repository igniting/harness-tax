#!/usr/bin/env python3
"""
opus-microbench runner.

Usage:
  export ANTHROPIC_API_KEY=...
  python3 harness/runner.py --models claude-opus-4-6 claude-opus-4-8 \
      --samples 3 --effort high --out results/run1.jsonl

Design notes:
- All models run with adaptive thinking. Effort is sent in output_config
  (supported on 4.6+; xhigh silently unsupported levels will 400 -> we retry
  without effort and record that).
- temperature/top_p/top_k are never set (4.7/4.8 reject non-default values).
- Thinking tokens are billed as output tokens and appear in usage.output_tokens.
- Each solution runs in a subprocess with a hard timeout; no network is used
  by any problem.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parent.parent
PROBLEMS_DIR = ROOT / "problems"

# $/MTok (input, output). Adjust if pricing changes.
PRICES = {
    "claude-opus-4-6": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
}

CODE_BLOCK_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.S)


def extract_code(text: str):
    blocks = CODE_BLOCK_RE.findall(text)
    if not blocks:
        return None
    return max(blocks, key=len)  # largest block = the module


def call_model(client, model, prompt, effort, max_tokens, max_retries=5):
    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    if effort:
        kwargs["output_config"] = {"effort": effort}
    attempt = 0
    while True:
        try:
            t0 = time.time()
            with client.messages.stream(**{k: v for k, v in kwargs.items()}) as stream:
                resp = stream.get_final_message()
            latency = time.time() - t0
            return resp, latency, bool(effort)
        except anthropic.BadRequestError as e:
            # e.g. effort/output_config unsupported on this model -> drop and retry once
            if "output_config" in kwargs:
                kwargs.pop("output_config")
                continue
            raise
        except (anthropic.RateLimitError, anthropic.APIStatusError) as e:
            attempt += 1
            if attempt > max_retries:
                raise
            wait = min(60, 2 ** attempt)
            print(f"    transient error ({type(e).__name__}), retry in {wait}s", file=sys.stderr)
            time.sleep(wait)


def run_tests(problem_dir: Path, code: str, timeout_s: int = 300):
    with tempfile.TemporaryDirectory() as td:
        sol = Path(td) / "solution.py"
        sol.write_text(code)
        env = dict(os.environ)
        env["SOLUTION_PATH"] = str(sol)
        env["PYTHONPATH"] = str(ROOT / "harness")
        try:
            p = subprocess.run(
                [sys.executable, "-m", "pytest", str(problem_dir / "tests"), "-q",
                 "--timeout", str(timeout_s)] if _has_pytest_timeout() else
                [sys.executable, "-m", "pytest", str(problem_dir / "tests"), "-q"],
                capture_output=True, text=True, timeout=timeout_s, env=env,
                cwd=str(ROOT),
            )
            passed = p.returncode == 0
            tail = (p.stdout or "").strip().splitlines()[-1:] or [""]
            return passed, tail[0]
        except subprocess.TimeoutExpired:
            return False, "TIMEOUT"


def _has_pytest_timeout():
    try:
        import pytest_timeout  # noqa
        return True
    except ImportError:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--problems", nargs="+", default=None,
                    help="subset of problem dir names; default all")
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--effort", default="high",
                    help="effort level sent in output_config; 'none' to omit")
    ap.add_argument("--max-tokens", type=int, default=32000)
    ap.add_argument("--out", default="results/results.jsonl")
    args = ap.parse_args()

    effort = None if args.effort == "none" else args.effort
    client = anthropic.Anthropic()

    problems = sorted(
        d for d in PROBLEMS_DIR.iterdir()
        if d.is_dir() and (not args.problems or d.name in args.problems)
    )
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_dir = ROOT / "results" / "transcripts"

    with open(out_path, "a") as f:
        for model in args.models:
            for prob in problems:
                prompt = (prob / "prompt.md").read_text()
                for s in range(args.samples):
                    print(f"[{model}] {prob.name} sample {s+1}/{args.samples} ...")
                    resp, latency, effort_used = call_model(
                        client, model, prompt, effort, args.max_tokens)
                    text = "".join(
                        b.text for b in resp.content if b.type == "text")
                    # Save transcript
                    t_dir = transcript_dir / model / prob.name
                    t_dir.mkdir(parents=True, exist_ok=True)
                    (t_dir / f"sample_{s}.txt").write_text(text)
                    code = extract_code(text)
                    if code is None:
                        passed, detail = False, "NO_CODE_BLOCK"
                        code_chars = 0
                    else:
                        passed, detail = run_tests(prob, code)
                        code_chars = len(code)
                    u = resp.usage
                    inp, outp = u.input_tokens, u.output_tokens
                    pin, pout = PRICES.get(model, (5.0, 25.0))
                    cost = inp / 1e6 * pin + outp / 1e6 * pout
                    rec = {
                        "model": model,
                        "problem": prob.name,
                        "sample": s,
                        "passed": passed,
                        "detail": detail,
                        "input_tokens": inp,
                        "output_tokens": outp,   # includes thinking tokens
                        "cost_usd": round(cost, 6),
                        "latency_s": round(latency, 2),
                        "effort": args.effort if effort_used else "omitted",
                        "text_chars": len(text),
                        "code_chars": code_chars,   # verbosity = text - code
                        "stop_reason": resp.stop_reason,
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    }
                    f.write(json.dumps(rec) + "\n")
                    f.flush()
                    print(f"    passed={passed} out_tokens={outp} "
                          f"cost=${cost:.4f} ({detail})")
    print(f"\nDone. Results in {out_path}. Run: python3 harness/report.py {out_path}")


if __name__ == "__main__":
    main()
