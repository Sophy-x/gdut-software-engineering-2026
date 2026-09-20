"""Small recursive-descent parser used by the grader and tests."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import re

from expression import Expr
from fraction_utils import parse_number


TOKEN_RE = re.compile(r"\s*(?:(\d+(?:[\u0027\u2019]\d+/\d+|/\d+)?)|([()+\-×÷*/]))")


@dataclass
class TokenStream:
    tokens: list[str]
    index: int = 0

    def peek(self) -> str | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def take(self, expected: str | None = None) -> str:
        token = self.peek()
        if token is None:
            raise ValueError("unexpected end of expression")
        if expected is not None and token != expected:
            raise ValueError(f"expected {expected}, got {token}")
        self.index += 1
        return token


def tokenize(text: str) -> list[str]:
    text = text.strip()
    if text.endswith("="):
        text = text[:-1].rstrip()
    if not text:
        raise ValueError("empty expression")
    tokens: list[str] = []
    position = 0
    while position < len(text):
        match = TOKEN_RE.match(text, position)
        if not match:
            raise ValueError(f"invalid expression near: {text[position:]}")
        tokens.append(match.group(1) or match.group(2))
        position = match.end()
    return tokens


def parse_expression(text: str) -> Expr:
    stream = TokenStream(tokenize(text))

    def parse_add_sub() -> Expr:
        node = parse_mul_div()
        while stream.peek() in ("+", "-"):
            op = stream.take()
            node = Expr.binary(op, node, parse_mul_div())
        return node

    def parse_mul_div() -> Expr:
        node = parse_atom()
        while stream.peek() in ("×", "÷", "*", "/"):
            op = stream.take()
            node = Expr.binary("×" if op == "*" else "÷" if op == "/" else op, node, parse_atom())
        return node

    def parse_atom() -> Expr:
        token = stream.peek()
        if token == "(":
            stream.take("(")
            node = parse_add_sub()
            stream.take(")")
            return node
        if token is None:
            raise ValueError("missing operand")
        if token in ("+", "-", "×", "÷", "*", "/", ")"):
            raise ValueError(f"unexpected token: {token}")
        stream.take()
        return Expr.leaf(parse_number(token))

    result = parse_add_sub()
    if stream.peek() is not None:
        raise ValueError(f"unexpected token: {stream.peek()}")
    return result


def parse_answer(text: str) -> Fraction:
    """Parse one answer line; accept an optional ``n:`` prefix."""
    candidate = text.strip()
    candidate = re.sub(r"^\s*\d+\s*[:.)]\s*", "", candidate)
    return parse_number(candidate)
