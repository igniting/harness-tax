#!/usr/bin/env python3
"""Oracle strength check: every reference must pass, every mutant must fail."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(sol, tests):
    env = dict(os.environ)
    env["SOLUTION_PATH"] = str(sol)
    env["PYTHONPATH"] = str(ROOT / "harness")
    p = subprocess.run([sys.executable, "-m", "pytest", str(tests), "-q"],
                       capture_output=True, text=True, env=env, cwd=str(ROOT),
                       timeout=600)
    return p.returncode == 0


def main():
    ok = True
    for prob in sorted((ROOT / "problems").iterdir()):
        if not prob.is_dir():
            continue
        tests = prob / "tests"
        ref = prob / "reference.py"
        good = run(ref, tests)
        print(f"{prob.name:<22} reference: {'PASS' if good else '** FAIL **'}")
        ok &= good
        mdir = prob / "mutants"
        if mdir.exists():
            for m in sorted(mdir.glob("*.py")):
                killed = not run(m, tests)
                print(f"{'':<22} mutant {m.name:<24} {'KILLED' if killed else '** SURVIVED **'}")
                ok &= killed
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
