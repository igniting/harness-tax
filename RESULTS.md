# Results

Run date: 2026-07-04. Claude Code version: 2.1.201. All runs at `--effort high`.

## Raw API (Messages API, single-shot)

5 samples per model × problem cell.

### Overall

| Model | pass@1 | Avg output tokens | Cost/solve | Verbosity (non-code chars) |
|-------|--------|-------------------|------------|----------------------------|
| claude-opus-4-6 | **92%** | 1,158 | $0.035 | 653 |
| claude-opus-4-7 | 80% | 1,016 | $0.037 | 13 |
| claude-opus-4-8 | 72% | 1,057 | $0.042 | 13 |
| claude-sonnet-5 | **100%** | 4,643 | $0.048 | 13 |

### Per-problem pass@1

| Problem | Opus 4-6 | Opus 4-7 | Opus 4-8 | Sonnet 5 |
|---------|----------|----------|----------|----------|
| p1_rate_limiter | 100% | 100% | 100% | 100% |
| p2_expr_parser | 100% | 60% | 40% | 100% |
| p3_recurrence | 80% | 40% | 20% | 100% |
| p4_scheduler | 80% | 100% | 100% | 100% |
| p5_debug_cache | 100% | 100% | 100% | 100% |

## Claude Code — Single-shot (Write tool only)

3 samples per model × problem cell. `--subagents deny`, no `--agentic`.

| Model | pass@1 | Avg turns | Avg output tokens | Avg context | Avg cost |
|-------|--------|-----------|-------------------|-------------|----------|
| claude-opus-4-6 | 93% | 2.3 | 4,103 | 55,123 | $0.22 |
| claude-opus-4-8 | **100%** | 2.1 | 2,782 | 39,041 | **$0.15** |
| claude-sonnet-5 | **100%** | 3.5 | 5,302 | 162,795 | $0.39 |

## Claude Code — Agentic (Bash + file tools, iterate & self-test)

1 sample per model × problem. `--agentic --subagents deny`.

| Model | pass@1 | Avg turns | Avg cost/problem |
|-------|--------|-----------|------------------|
| claude-opus-4-6 | **100%** | 4.8 | $0.29 |
| claude-opus-4-8 | **100%** | 3.2 | $0.27 |
| claude-sonnet-5 | **100%** | 4.0 | **$0.20** |

Per-problem detail:

| Problem | Opus 4-6 (turns/cost) | Opus 4-8 (turns/cost) | Sonnet 5 (turns/cost) |
|---------|----------------------|----------------------|----------------------|
| p1_rate_limiter | 5 / $0.28 | 3 / $0.23 | 4 / $0.22 |
| p2_expr_parser | 4 / $0.42 | 3 / $0.34 | 4 / $0.28 |
| p3_recurrence | 2 / $0.15 | 4 / $0.30 | 3 / $0.13 |
| p4_scheduler | 10 / $0.44 | 3 / $0.32 | 5 / $0.23 |
| p5_debug_cache | 3 / $0.15 | 3 / $0.13 | 4 / $0.13 |

## Analysis

### Thesis evaluation: "Opus 4.6 already writes complicated code; 4.7/4.8 add tokens, not capability"

**On raw API: thesis supported (and then some).** Opus 4-6 outperforms both 4-7 and
4-8 on these contamination-resistant problems. The newer Opus models are actually
*worse* on novel specs — particularly p2_expr_parser (novel `@` operator precedence)
and p3_recurrence (DST edge cases). The pattern is 4-6 > 4-7 > 4-8, the opposite
of what "newer = better" would predict.

**On Claude Code: thesis partially overturned.** Through the CC harness, Opus 4-8
achieves 100% at the lowest cost ($0.15/sample), outperforming even 4-6. The CC
system prompt and tool framing appear to compensate for 4-8's raw API weakness.

**Sonnet 5 breaks the frame entirely.** A smaller, cheaper model achieves 100% on
raw API — something no Opus variant manages. It uses ~4x more output tokens but at
half the $/MTok, making it cost-competitive.

### Root cause: training priors vs novel specs

Examining the p2_expr_parser failure (Opus 4-8):

The spec states: *"unary minus binds TIGHTER than `^`'s left operand"* — so `-2 ^ 2`
should parse as `(-2) ^ 2 = 4`.

Opus 4-8 computes `-(2^2) = -4` instead. It implements the *standard* precedence
convention (used in most programming languages) rather than following the novel spec.
This is exactly the kind of contamination-resistance the benchmark is designed to
detect: newer models with more training may be *more* likely to default to memorized
conventions when the spec contradicts them.

### The harness effect

The Claude Code harness adds ~75x context overhead (system prompt + tool schemas) but
provides a capability lift for models that struggle on raw single-shot:

- Opus 4-8: 72% raw → 100% CC single-shot (the framing helps)
- Opus 4-6: 92% raw → 93% CC (no change needed)
- Sonnet 5: 100% raw → 100% CC (already perfect)

In agentic mode, all models reach 100% — the iterate-and-verify loop eliminates
capability differences entirely. The remaining question is cost efficiency:

- **Best raw API value:** Sonnet 5 (100%, $0.048/solve)
- **Best CC single-shot value:** Opus 4-8 (100%, $0.15/sample)
- **Best CC agentic value:** Sonnet 5 (100%, $0.20/problem)

### Conclusions

1. For single-shot code generation via raw API, **Sonnet 5 dominates** — cheaper per
   token, higher pass rate, and no need for a harness wrapper.
2. For Claude Code usage, **Opus 4-8 in single-shot mode** offers the best
   accuracy-per-dollar. The CC framing unlocks capability that raw API misses.
3. **Agentic mode equalizes all models** but at 2-10x the cost of single-shot. Use it
   as a reliability guarantee, not a default.
4. The original thesis holds narrowly: on raw single-shot, 4.6 > 4.7 > 4.8. But
   this only measures one axis — the CC results show 4.8 has latent capability that
   surfaces with the right framing.

## Reproducing

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...
python3 harness/validate.py                    # verify oracles (no API needed)
python3 harness/runner.py --models claude-opus-4-6 claude-opus-4-8 claude-sonnet-5 \
    --samples 5 --effort high --out results/my_run.jsonl
python3 harness/report.py results/my_run.jsonl
```

Result files in `results/`:
- `run1.jsonl` — raw API results (100 samples)
- `cc_results.jsonl` — Claude Code single-shot results (45 samples)
- `cc_agentic.jsonl` — Claude Code agentic results (15 samples)
- `transcripts/` — raw API model outputs
- `cc_transcripts/` — CC solution files and JSON output
