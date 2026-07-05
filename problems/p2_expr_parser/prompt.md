Implement a Python module with a single function:

    evaluate(expr: str) -> int

which evaluates expressions in the "Calc-26" language over arbitrary-precision integers.

Grammar (whitespace between tokens allowed and ignored):
- Integer literals: one or more digits (no sign in the literal itself).
- Parentheses for grouping.
- Unary minus: may be applied repeatedly, e.g. `--5`.
- Binary operators, from LOWEST to HIGHEST precedence:
    1. `@`  (midpoint)      — left-associative
    2. `+`, `-`             — left-associative
    3. `*`, `/`             — left-associative
    4. `^`  (power)         — RIGHT-associative
- Unary minus binds TIGHTER than `^`'s left operand but the whole `^` expression:
  precisely, `-2 ^ 2` parses as `(-2) ^ 2 = 4`, while `2 ^ -2` is a syntax error
  unless parenthesized as `2 ^ (-2)` — a unary minus may not directly follow `^`,
  `*`, `/`, `+`, `-`, or `@` EXCEPT it may follow `+`, `-`, `@`, `*`, `/` (i.e. only
  directly after `^` is it forbidden).

Semantics:
- `a @ b`  = floor((a + b) / 2)   (floor toward negative infinity)
- `a / b`  = floor division toward negative infinity (Python `//`). Division by zero
  must raise `ZeroDivisionError`.
- `a ^ b`  = a raised to the power b. If b < 0, raise `ValueError`.
- All other operators have usual integer semantics.

Errors:
- Any malformed input (unknown characters, dangling operators, empty input,
  unbalanced parens, unary minus directly after `^`) must raise `ValueError`.
- Do NOT use Python's `eval`/`exec` or the `ast` module.

Examples:
    evaluate("1 @ 2")            == 1
    evaluate("1 @ 2 @ 10")       == 5      # left-assoc: (1@2)@10 = 1@10... careful: (1@2)=1, 1@10=5
    evaluate("2 ^ 3 ^ 2")        == 512    # right-assoc
    evaluate("-2 ^ 2")           == 4
    evaluate("7 / -1")           -> after `/` unary minus IS allowed: equals -7
    evaluate("3 + 4 @ 10")       == 8      # @ binds looser than +: (3+4) @ 10 = 3
                                           # correction: (3+4)=7, 7@10 = floor(17/2)=8
    evaluate("2 ^ -2")           raises ValueError

Return ONE complete Python module in a single ```python code block. No prose outside the block.
