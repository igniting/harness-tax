def evaluate(expr: str) -> int:
    tokens = _tokenize(expr)
    p = _Parser(tokens)
    val = p.parse_mid()
    if p.peek() is not None:
        raise ValueError("trailing input")
    return val


def _tokenize(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c.isspace():
            i += 1
        elif c.isdigit():
            j = i
            while j < len(s) and s[j].isdigit():
                j += 1
            out.append(("num", int(s[i:j])))
            i = j
        elif c in "+-*/@^()":
            out.append((c, None))
            i += 1
        else:
            raise ValueError(f"bad char {c!r}")
    return out


class _Parser:
    def __init__(self, tokens):
        self.toks = tokens
        self.i = 0

    def peek(self):
        return self.toks[self.i][0] if self.i < len(self.toks) else None

    def take(self):
        t = self.toks[self.i]
        self.i += 1
        return t

    # level 1: @  (lowest), left-assoc
    def parse_mid(self):
        v = self.parse_add()
        while self.peek() == "@":
            self.take()
            r = self.parse_add()
            v = (v + r) // 2
        return v

    # level 2: + -, left-assoc
    def parse_add(self):
        v = self.parse_mul()
        while self.peek() in ("+", "-"):
            op = self.take()[0]
            r = self.parse_mul()
            v = v + r if op == "+" else v - r
        return v

    # level 3: * /, left-assoc
    def parse_mul(self):
        v = self.parse_unary()
        while self.peek() in ("*", "/"):
            op = self.take()[0]
            r = self.parse_unary()
            if op == "*":
                v = v * r
            else:
                if r == 0:
                    raise ZeroDivisionError("division by zero")
                v = v // r
        return v

    # unary minus applies to the atom BEFORE ^ : -2^2 == (-2)^2
    def parse_unary(self):
        neg = False
        while self.peek() == "-":
            self.take()
            neg = not neg
        v = self.parse_atom()
        if neg:
            v = -v
        if self.peek() == "^":
            self.take()
            r = self.parse_pow_rhs()
            v = _pow(v, r)
        return v

    # rhs of ^: right-assoc chain, unary minus forbidden at its head
    def parse_pow_rhs(self):
        if self.peek() == "-":
            raise ValueError("unary minus not allowed directly after ^")
        v = self.parse_atom()
        if self.peek() == "^":
            self.take()
            r = self.parse_pow_rhs()
            v = _pow(v, r)
        return v

    def parse_atom(self):
        t = self.peek()
        if t == "num":
            return self.take()[1]
        if t == "(":
            self.take()
            v = self.parse_mid()
            if self.peek() != ")":
                raise ValueError("expected )")
            self.take()
            return v
        raise ValueError(f"unexpected token {t!r}")


def _pow(a, b):
    if b < 0:
        raise ValueError("negative exponent")
    return a ** b
