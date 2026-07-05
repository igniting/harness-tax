"""Evaluator for the "Calc-26" arbitrary-precision integer expression language.

Grammar (lowest to highest precedence):
    @               (left-assoc, midpoint)
    + -             (left-assoc)
    * /             (left-assoc)
    ^               (right-assoc, power)
    unary -         (binds tighter than ^'s left operand, forbidden directly
                     after ^ unless parenthesized)
    ( expr )
    NUMBER
"""


class _Token:
    __slots__ = ("kind", "value")

    def __init__(self, kind, value=None):
        self.kind = kind
        self.value = value

    def __repr__(self):
        return f"_Token({self.kind!r}, {self.value!r})"


_SIMPLE_TOKENS = set("()@+-*/^")


def _tokenize(expr):
    tokens = []
    i = 0
    n = len(expr)
    while i < n:
        c = expr[i]
        if c.isspace():
            i += 1
            continue
        if c.isdigit():
            j = i
            while j < n and expr[j].isdigit():
                j += 1
            tokens.append(_Token("NUM", int(expr[i:j])))
            i = j
            continue
        if c in _SIMPLE_TOKENS:
            tokens.append(_Token(c))
            i += 1
            continue
        raise ValueError(f"Unexpected character {c!r} in expression")
    return tokens


class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def _peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _peek_kind(self):
        tok = self._peek()
        return tok.kind if tok is not None else None

    def _advance(self):
        tok = self._peek()
        if tok is None:
            raise ValueError("Unexpected end of expression")
        self.pos += 1
        return tok

    def _expect(self, kind):
        tok = self._advance()
        if tok.kind != kind:
            raise ValueError(f"Expected {kind!r} but found {tok.kind!r}")
        return tok

    # @  (lowest precedence, left-assoc)
    def parse_at(self):
        left = self.parse_addsub()
        while self._peek_kind() == "@":
            self._advance()
            right = self.parse_addsub()
            left = (left + right) // 2
        return left

    # + -
    def parse_addsub(self):
        left = self.parse_muldiv()
        while self._peek_kind() in ("+", "-"):
            op = self._advance().kind
            right = self.parse_muldiv()
            left = left + right if op == "+" else left - right
        return left

    # * /
    def parse_muldiv(self):
        left = self.parse_pow()
        while self._peek_kind() in ("*", "/"):
            op = self._advance().kind
            right = self.parse_pow()
            if op == "*":
                left = left * right
            else:
                if right == 0:
                    raise ZeroDivisionError("division by zero")
                left = left // right
        return left

    # ^  (right-assoc)
    def parse_pow(self):
        left = self.parse_unary()
        if self._peek_kind() == "^":
            self._advance()
            if self._peek_kind() == "-":
                raise ValueError(
                    "Unary minus may not directly follow '^'; use parentheses"
                )
            right = self.parse_pow()
            if right < 0:
                raise ValueError("Exponent must be non-negative")
            left = left ** right
        return left

    # unary minus (may repeat) then primary
    def parse_unary(self):
        if self._peek_kind() == "-":
            self._advance()
            return -self.parse_unary()
        return self.parse_primary()

    def parse_primary(self):
        tok = self._peek()
        if tok is None:
            raise ValueError("Unexpected end of expression")
        if tok.kind == "NUM":
            self._advance()
            return tok.value
        if tok.kind == "(":
            self._advance()
            value = self.parse_at()
            self._expect(")")
            return value
        raise ValueError(f"Unexpected token {tok.kind!r}")


def evaluate(expr: str) -> int:
    tokens = _tokenize(expr)
    if not tokens:
        raise ValueError("Empty expression")
    parser = _Parser(tokens)
    result = parser.parse_at()
    if parser.pos != len(tokens):
        raise ValueError("Unexpected trailing tokens in expression")
    return result
