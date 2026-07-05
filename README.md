# harness-tax: Measuring What Agentic Harnesses Add (and Cost)

Does wrapping a model in an agentic harness (system prompts, tool schemas, turn
loops, self-verification) improve code generation — and at what cost? This
benchmark measures the same problems across raw API calls and agentic harness
runs to quantify the tradeoff.

Uses contamination-resistant problems (invented specs not in training data) so
results reflect genuine reasoning, not memorized patterns.

See [RESULTS.md](RESULTS.md) for findings from our runs.

## What it measures

For each model × problem × sample:
- **pass@1** — does the generated code pass automated oracles?
- **output tokens** — how much does the model generate (including thinking)?
- **context tokens** — how much overhead does the harness add?
- **cost** — total spend per solved problem
- **turns** — how many iterations does the agentic loop need?

The key comparison: same model, same problem, raw API vs harness. The delta is
the harness tax (in tokens/cost) and the harness lift (in pass rate).

## Problems

| id | tests for | oracle |
|----|-----------|--------|
| p1_rate_limiter | stateful invariants, boundary semantics | differential vs brute-force reference (random streams) |
| p2_expr_parser | precedence/associativity with a novel operator, adversarial spec quirk | random-AST differential + pinned spec examples |
| p3_recurrence | DST gaps/overlaps, half-hour zones | independent minute-scan oracle around real 2026 transitions |
| p4_scheduler | deterministic multi-worker DAG simulation, tie-breaking | independent unit-time-step simulator |
| p5_debug_cache | find-and-fix 5 planted bugs without breaking the API | independent list-based oracle + targeted units |

p1/p2 ship with mutants; `harness/validate.py` proves the oracles kill them.

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...
```

## Run

### 1. Raw API (baseline)

```bash
python3 harness/runner.py \
    --models claude-opus-4-6 claude-opus-4-8 claude-sonnet-5 \
    --samples 5 --effort high --out results/run1.jsonl
python3 harness/report.py results/run1.jsonl
```

### 2. Agentic harness (Claude Code)

```bash
npm install -g @anthropic-ai/claude-code
# single-shot (write-only, no iteration)
python3 harness/cc_runner.py --models claude-opus-4-6 claude-opus-4-8 claude-sonnet-5 --samples 3 --subagents deny
# agentic (can run tests, iterate, self-fix)
python3 harness/cc_runner.py --models claude-opus-4-6 claude-opus-4-8 claude-sonnet-5 --samples 1 --agentic --subagents deny
# compare
python3 harness/cc_report.py results/cc_results.jsonl results/run1.jsonl
```

### 3. Oracle validation (no API needed)

```bash
python3 harness/validate.py
```

## What each axis isolates

- **Raw API vs harness single-shot**: the fixed cost of the harness — system
  prompt, tool schemas, turn loop, cache churn. Reported as `ctx_ratio`.
- **Single-shot vs agentic**: what iterate-and-self-verify buys in pass@1 and
  what it costs in tokens/turns.
- **Subagents deny vs allow**: the fan-out overhead.

Transcripts are saved to `results/transcripts/` (raw API) and
`results/cc_transcripts/` (harness runs).

## Notes

- Run all models at the same effort level for fair comparison.
- Runs execute in isolated temp workspaces with no persistent config.
- 5 problems × N samples is a signal, not a proof. Use ≥5 samples/cell.
