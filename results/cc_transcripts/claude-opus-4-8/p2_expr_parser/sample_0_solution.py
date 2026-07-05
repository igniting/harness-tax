"""Calc-26 language evaluator over arbitrary-precision integers.

Public API:
    evaluate(expr: str) -> int

Precedence (lowest -> highest):
    @            midpoint, left-associative
    + -          left-associative
    * /          left-associative
    ^            power, right-associative

Unary minus binds tighter than the left operand of `^` (so `-2 ^ 2 == 4`),
and a unary minus may appear directly after `+ - * / @` but NOT directly
after `^` (so `2 ^ -2` is a syntax error while `2 ^ (-2)` is a value error).
"""


def _tokenize(expr):
    """Turn the source string into a list of tokens.

    Integer literals become Python ``int`` tokens; every operator and
    parenthesis becomes a single-character ``str`` token.  Unknown
    characters raise ``ValueError``.
    """
    tokens = []
    i = 0
    n = len(expr)
    operators = set("@+-*/^()")
    while i < n:
        c = expr[i]
        if c.isspace():
            i += 1
            continue
        if c.isdigit():
            j = i
            while j < n and expr[j].isdigit():
                j += 1
            tokens.append(int(expr[i:j]))
            i = j
            continue
        if c in operators:
            tokens.append(c)
            i += 1
            continue
        raise ValueError("unknown character: {!r}".format(c))
    return tokens


class _Parser:
    def __init__(self, tokens):
        self.toks = tokens
        self.pos = 0

    def _peek(self):
        if self.pos < len(self.toks):
            return self.toks[self.pos]
        return None

    def _advance(self):
        tok = self.toks[self.pos]
        self.pos += 1
        return tok

    def at_end(self):
        return self.pos >= len(self.toks)

    # @ : lowest precedence, left-associative
    def parse_at(self):
        left = self.parse_add()
        while self._peek() == "@":
            self._advance()
            right = self.parse_add()
            left = (left + right) // 2  # floor toward -inf
        return left

    # + - : left-associative
    def parse_add(self):
        left = self.parse_mul()
        while self._peek() in ("+", "-"):
            op = self._advance()
            right = self.parse_mul()
            if op == "+":
                left = left + right
            else:
                left = left - right
        return left

    # * / : left-associative
    def parse_mul(self):
        left = self.parse_pow()
        while self._peek() in ("*", "/"):
            op = self._advance()
            right = self.parse_pow()
            if op == "*":
                left = left * right
            else:
                left = left // right  # floor division; raises ZeroDivisionError
        return left

    # ^ : right-associative, base may carry a unary minus
    def parse_pow(self):
        base = self.parse_unary()
        if self._peek() == "^":
            self._advance()
            exp = self.parse_exponent()
            if exp < 0:
                raise ValueError("negative exponent")
            return base ** exp
        return base

    # right operand of ^: unary minus is NOT allowed here directly
    def parse_exponent(self):
        base = self.parse_atom()
        if self._peek() == "^":
            self._advance()
            exp = self.parse_exponent()
            if exp < 0:
                raise ValueError("negative exponent")
            return base ** exp
        return base

    # unary minus, may be repeated
    def parse_unary(self):
        if self._peek() == "-":
            self._advance()
            return -self.parse_unary()
        return self.parse_atom()

    # integer literal or parenthesized expression
    def parse_atom(self):
        tok = self._peek()
        if tok == "(":
            self._advance()
            val = self.parse_at()
            if self._peek() != ")":
                raise ValueError("unbalanced parentheses")
            self._advance()
            return val
        if isinstance(tok, int):
            self._advance()
            return tok
        raise ValueError("unexpected token: {!r}".format(tok))


def evaluate(expr):
    """Evaluate a Calc-26 expression and return the integer result."""
    if not isinstance(expr, str):
        raise ValueError("expression must be a string")
    tokens = _tokenize(expr)
    if not tokens:
        raise ValueError("empty input")
    parser = _Parser(tokens)
    result = parser.parse_at()
    if not parser.at_end():
        raise ValueError("trailing tokens")
    return result
