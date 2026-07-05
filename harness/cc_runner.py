#!/usr/bin/env python3
"""
opus-microbench: Claude Code harness runner.

Runs the same problems through Claude Code headless mode instead of the raw
Messages API, so harness overhead (system prompt, tool schemas, cache churn,
turn loop, optional subagent fan-out) is measured, not assumed.

  export ANTHROPIC_API_KEY=...   # or be logged in via `claude /login`
  python3 harness/cc_runner.py \
      --models claude-opus-4-6 claude-opus-4-8 \
      --samples 3 --effort high --agentic --subagents deny \
      --out results/cc_run1.jsonl

Axes:
  --agentic          allow Bash+file tools so the model can iterate/self-test
                     (realistic Claude Code usage). Without it, single-shot:
                     write solution.py and stop.
  --subagents allow|deny   deny adds `--disallowedTools Task` (no fan-out).
                     Run both to isolate the subagent tax.

Comparisons this enables against api runner output (see cc_report.py):
  harness_overhead = (input + cache_creation + cache_read + output)_cc
                     / (input + output)_raw_api        per model x problem
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBLEMS_DIR = ROOT / "problems"

SINGLE_SHOT_SUFFIX = """

---
Write the complete module described above to a file named `solution.py` in the
current directory. Write the file and stop. Do not create any other files, do
not run tests, do not use git.
"""

AGENTIC_SUFFIX = """

---
Write the complete module described above to a file named `solution.py` in the
current directory. You may write scratch tests and run them to verify your
solution before finishing, but the graded artifact is solution.py only.
Do not use git. Stop when you are confident solution.py is correct.
"""


def build_cmd(model, effort, agentic, subagents, workspace):
    cmd = [
        "claude", "-p",
        "--model", model,
        "--output-format", "json",
        "--no-session-persistence",
        "--strict-mcp-config",
    ]
    if effort:
        cmd += ["--effort", effort]
    if agentic:
        # full local toolset, permissions bypassed inside the isolated workspace
        cmd += ["--dangerously-skip-permissions"]
    else:
        cmd += ["--allowedTools", "Write", "--permission-mode", "acceptEdits"]
    if subagents == "deny":
        cmd += ["--disallowedTools", "Task"]
    return cmd


def run_claude(prompt, cmd, workspace, timeout_s):
    env = dict(os.environ)
    env.setdefault("DISABLE_AUTOUPDATER", "1")
    env.setdefault("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "1")
    t0 = time.time()
    try:
        p = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True,
            timeout=timeout_s, env=env, cwd=str(workspace),
        )
    except subprocess.TimeoutExpired:
        return None, time.time() - t0, "WALL_TIMEOUT"
    wall = time.time() - t0
    out = (p.stdout or "").strip()
    # the JSON result is the last line / whole stdout in json mode
    try:
        data = json.loads(out.splitlines()[-1]) if out else None
    except json.JSONDecodeError:
        data = None
    err = None if data else f"BAD_JSON rc={p.returncode}: {out[:200]} {p.stderr[:200]}"
    return data, wall, err


def run_tests(problem_dir, solution_path, timeout_s=300):
    env = dict(os.environ)
    env["SOLUTION_PATH"] = str(solution_path)
    env["PYTHONPATH"] = str(ROOT / "harness")
    try:
        p = subprocess.run(
            [sys.executable, "-m", "pytest", str(problem_dir / "tests"), "-q"],
            capture_output=True, text=True, timeout=timeout_s, env=env,
            cwd=str(ROOT),
        )
        tail = (p.stdout or "").strip().splitlines()[-1:] or [""]
        return p.returncode == 0, tail[0]
    except subprocess.TimeoutExpired:
        return False, "TEST_TIMEOUT"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--problems", nargs="+", default=None)
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--effort", default="high", help="'none' to omit --effort")
    ap.add_argument("--agentic", action="store_true",
                    help="allow Bash/file tools for iterate-and-verify")
    ap.add_argument("--subagents", choices=["allow", "deny"], default="deny")
    ap.add_argument("--timeout", type=int, default=900,
                    help="wall-clock seconds per run")
    ap.add_argument("--out", default="results/cc_results.jsonl")
    args = ap.parse_args()

    if shutil.which("claude") is None:
        sys.exit("claude CLI not found. npm install -g @anthropic-ai/claude-code")
    cc_version = subprocess.run(["claude", "--version"], capture_output=True,
                                text=True).stdout.strip()
    print(f"claude code version: {cc_version}")

    effort = None if args.effort == "none" else args.effort
    suffix = AGENTIC_SUFFIX if args.agentic else SINGLE_SHOT_SUFFIX
    problems = sorted(
        d for d in PROBLEMS_DIR.iterdir()
        if d.is_dir() and (not args.problems or d.name in args.problems)
    )
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    transcript_dir = ROOT / "results" / "cc_transcripts"

    with open(out_path, "a") as f:
        for model in args.models:
            for prob in problems:
                prompt = (prob / "prompt.md").read_text() + suffix
                for s in range(args.samples):
                    print(f"[cc:{model}] {prob.name} sample {s+1}/{args.samples} "
                          f"(agentic={args.agentic}, subagents={args.subagents}) ...")
                    with tempfile.TemporaryDirectory() as ws:
                        cmd = build_cmd(model, effort, args.agentic,
                                        args.subagents, ws)
                        data, wall, err = run_claude(prompt, cmd, ws, args.timeout)
                        sol = Path(ws) / "solution.py"
                        if sol.exists():
                            passed, detail = run_tests(prob, sol)
                        else:
                            passed, detail = False, err or "NO_SOLUTION_FILE"
                        # Save transcripts
                        t_dir = transcript_dir / model / prob.name
                        t_dir.mkdir(parents=True, exist_ok=True)
                        if sol.exists():
                            shutil.copy2(sol, t_dir / f"sample_{s}_solution.py")
                        if data:
                            (t_dir / f"sample_{s}_output.json").write_text(
                                json.dumps(data, indent=2))
                        u = (data or {}).get("usage", {})
                        rec = {
                            "harness": "claude-code",
                            "cc_version": cc_version,
                            "model": model,
                            "problem": prob.name,
                            "sample": s,
                            "agentic": args.agentic,
                            "subagents": args.subagents,
                            "effort": args.effort,
                            "passed": passed,
                            "detail": detail,
                            "num_turns": (data or {}).get("num_turns"),
                            "input_tokens": u.get("input_tokens", 0),
                            "output_tokens": u.get("output_tokens", 0),
                            "cache_creation_tokens": u.get("cache_creation_input_tokens", 0),
                            "cache_read_tokens": u.get("cache_read_input_tokens", 0),
                            "total_cost_usd": (data or {}).get("total_cost_usd"),
                            "duration_api_s": ((data or {}).get("duration_api_ms") or 0) / 1000,
                            "wall_s": round(wall, 1),
                            "model_usage": (data or {}).get("modelUsage", {}),
                            "is_error": (data or {}).get("is_error"),
                            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        }
                        f.write(json.dumps(rec) + "\n")
                        f.flush()
                        total_ctx = (rec["input_tokens"]
                                     + rec["cache_creation_tokens"]
                                     + rec["cache_read_tokens"])
                        print(f"    passed={passed} turns={rec['num_turns']} "
                              f"out={rec['output_tokens']} ctx_total={total_ctx} "
                              f"cost=${rec['total_cost_usd']} ({detail})")
    print(f"\nDone. Results in {out_path}. "
          f"Compare vs raw API: python3 harness/cc_report.py {out_path} results/results.jsonl")


if __name__ == "__main__":
    main()
