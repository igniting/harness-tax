def evaluate(expr: str) -> int:
    tokens = _tokenize(expr)
    if not tokens:
        raise ValueError("Empty expression")
    parser = _Parser(tokens)
    result = parser.parse_expr()
    if parser.pos < len(parser.tokens):
        raise ValueError("Unexpected token after expression")
    return result


def _tokenize(expr):
    tokens = []
    i = 0
    while i < len(expr):
        c = expr[i]
        if c.isspace():
            i += 1
        elif c.isdigit():
            j = i
            while j < len(expr) and expr[j].isdigit():
                j += 1
            tokens.append(('INT', int(expr[i:j])))
            i = j
        elif c in '+-*/^@()':
            tokens.append(('OP', c))
            i += 1
        else:
            raise ValueError(f"Unknown character: {c}")
    return tokens


class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, typ, val=None):
        tok = self.peek()
        if tok is None or tok[0] != typ or (val is not None and tok[1] != val):
            raise ValueError("Expected token not found")
        return self.consume()

    def parse_expr(self):
        return self.parse_midpoint()

    def parse_midpoint(self):
        left = self.parse_addition()
        while self.peek() == ('OP', '@'):
            self.consume()
            right = self.parse_addition()
            left = (left + right) // 2
        return left

    def parse_addition(self):
        left = self.parse_multiply()
        while self.peek() and self.peek()[0] == 'OP' and self.peek()[1] in ('+', '-'):
            op = self.consume()[1]
            right = self.parse_multiply()
            if op == '+':
                left = left + right
            else:
                left = left - right
        return left

    def parse_multiply(self):
        left = self.parse_power()
        while self.peek() and self.peek()[0] == 'OP' and self.peek()[1] in ('*', '/'):
            op = self.consume()[1]
            right = self.parse_power()
            if op == '*':
                left = left * right
            else:
                if right == 0:
                    raise ZeroDivisionError("Division by zero")
                left = left // right
        return left

    def parse_power(self):
        base = self.parse_unary()
        if self.peek() == ('OP', '^'):
            self.consume()
            exp = self._parse_power_no_unary()
            if exp < 0:
                raise ValueError("Negative exponent")
            return base ** exp
        return base

    def _parse_power_no_unary(self):
        if self.peek() == ('OP', '-'):
            raise ValueError("Unary minus not allowed directly after ^")
        base = self.parse_atom()
        if self.peek() == ('OP', '^'):
            self.consume()
            exp = self._parse_power_no_unary()
            if exp < 0:
                raise ValueError("Negative exponent")
            return base ** exp
        return base

    def parse_unary(self):
        if self.peek() == ('OP', '-'):
            self.consume()
            operand = self.parse_unary()
            return -operand
        return self.parse_atom()

    def parse_atom(self):
        tok = self.peek()
        if tok is None:
            raise ValueError("Unexpected end of expression")
        if tok[0] == 'INT':
            self.consume()
            return tok[1]
        if tok == ('OP', '('):
            self.consume()
            result = self.parse_expr()
            self.expect('OP', ')')
            return result
        raise ValueError(f"Unexpected token: {tok}")
