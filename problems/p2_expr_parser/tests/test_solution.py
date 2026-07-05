import random
import pytest
from bench_common.loader import load_solution

sol = load_solution()
ev = sol.evaluate


def test_spec_examples():
    assert ev("1 @ 2") == 1
    assert ev("1 @ 2 @ 10") == 5
    assert ev("2 ^ 3 ^ 2") == 512
    assert ev("-2 ^ 2") == 4
    assert ev("7 / -1") == -7
    assert ev("3 + 4 @ 10") == 8
    assert ev("--5") == 5
    assert ev("(1+2)^2") == 9
    assert ev("-7 / 2") == -4          # floor toward -inf
    assert ev("0 @ -1") == -1          # floor midpoint: floor(-1/2) = -1
    assert ev("2 ^ 0") == 1
    assert ev("1 - 2 - 3") == -4       # left assoc
    assert ev("100 / 3 / 3") == 11


def test_errors():
    for bad in ["2 ^ -2", "", "1 +", "(1", "1)", "1 & 2", "^2", "1 2", "@1", "5 -"]:
        with pytest.raises(ValueError):
            ev(bad)
    with pytest.raises(ZeroDivisionError):
        ev("10 / (3 - 3)")
    with pytest.raises(ValueError):
        ev("2 ^ (0-1)")                # negative exponent -> ValueError


# ---- differential oracle: random ASTs, fully parenthesized rendering ----

def _floor_div(a, b):
    if b == 0:
        raise ZeroDivisionError
    return a // b


def gen(rng, depth):
    """Return (expr_string_fully_parenthesized, value_or_exception_class)."""
    if depth == 0 or rng.random() < 0.3:
        n = rng.randint(0, 30)
        if rng.random() < 0.25:
            return f"(-{n})", -n
        return str(n), n
    op = rng.choice(["@", "+", "-", "*", "/", "^"])
    ls, lv = gen(rng, depth - 1)
    rs, rv = gen(rng, depth - 1)
    if isinstance(lv, type) or isinstance(rv, type):
        # propagate first error; keep simple: regenerate instead
        return gen(rng, depth)
    if op == "@":
        return f"({ls} @ {rs})", (lv + rv) // 2
    if op == "+":
        return f"({ls} + {rs})", lv + rv
    if op == "-":
        return f"({ls} - {rs})", lv - rv
    if op == "*":
        return f"({ls} * {rs})", lv * rv
    if op == "/":
        if rv == 0:
            return f"({ls} / {rs})", ZeroDivisionError
        return f"({ls} / {rs})", _floor_div(lv, rv)
    if op == "^":
        if rv < 0:
            return f"({ls} ^ {rs})", ValueError
        if abs(lv) > 9 or rv > 9:      # keep magnitudes sane
            rv2 = rv % 4
            return f"({ls} ^ {rv2})", lv ** rv2
        return f"({ls} ^ {rs})", lv ** rv


def test_differential_random_asts():
    rng = random.Random(42026)
    for i in range(400):
        s, want = gen(rng, rng.randint(1, 5))
        if want is ZeroDivisionError:
            with pytest.raises(ZeroDivisionError):
                ev(s)
        elif want is ValueError:
            with pytest.raises(ValueError):
                ev(s)
        else:
            got = ev(s)
            assert got == want, f"expr={s}: got {got}, expected {want}"


def test_precedence_unparenthesized():
    rng = random.Random(777)
    # flat chains mixing @ with +: @ must bind loosest
    for _ in range(100):
        nums = [rng.randint(0, 20) for _ in range(4)]
        a, b, c, d = nums
        assert ev(f"{a} + {b} @ {c} + {d}") == ((a + b) + (c + d)) // 2
        assert ev(f"{a} * {b} + {c}") == a * b + c
        assert ev(f"{a} + {b} * {c}") == a + b * c
