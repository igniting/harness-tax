#!/usr/bin/env python3
"""Measure tokenizer inflation between model generations on identical text.

The 4.7+ generation uses a new tokenizer reported to produce up to ~1.35x more
tokens on the same text. This probe quantifies it on text YOU care about
(pass your own source files) so the benchmark can normalize per-token metrics.

  export ANTHROPIC_API_KEY=...
  python3 harness/tokenizer_probe.py claude-opus-4-6 claude-opus-4-8 -- file1.py file2.go
"""
import sys
from pathlib import Path

import anthropic

DEFAULT_SAMPLES = {
    "english_prose": "The verification layer routes each generated check to the "
    "cheapest oracle that can adjudicate it, weighting oracle trust by historical "
    "kill attribution across the mutation corpus." * 20,
    "python_code": (Path(__file__).parent.parent / "problems/p1_rate_limiter/reference.py").read_text() * 5,
}


def main():
    argv = sys.argv[1:]
    if "--" in argv:
        i = argv.index("--")
        models, files = argv[:i], argv[i + 1:]
    else:
        models, files = argv, []
    if not models:
        models = ["claude-opus-4-6", "claude-opus-4-8"]

    samples = dict(DEFAULT_SAMPLES)
    for fp in files:
        samples[fp] = Path(fp).read_text()

    client = anthropic.Anthropic()
    counts = {}
    for name, text in samples.items():
        counts[name] = {}
        for m in models:
            r = client.messages.count_tokens(
                model=m, messages=[{"role": "user", "content": text}])
            counts[name][m] = r.input_tokens

    base = models[0]
    print(f"{'sample':<24}" + "".join(f"{m:>22}" for m in models) + f"{'ratio vs ' + base:>18}")
    for name, c in counts.items():
        ratios = " / ".join(f"{c[m]/c[base]:.3f}" for m in models[1:])
        print(f"{name:<24}" + "".join(f"{c[m]:>22}" for m in models) + f"{ratios:>18}")
    print("\nUse the ratio to deflate 4.7+/Fable token counts when comparing "
          "per-token metrics against 4.6-era baselines.")


if __name__ == "__main__":
    main()
