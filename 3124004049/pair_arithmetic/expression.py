"""Expression tree, exact evaluation, rendering, and duplicate canonicalization."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from fraction_utils import format_fraction


OPS = ("+", "-", "×", "÷")
PRECEDENCE = {"+": 1, "-": 1, "×": 2, "÷": 2}


@dataclass(frozen=True)
class Expr:
    value: Fraction | None = None
    op: str | None = None
    left: "Expr | None" = None
    right: "Expr | None" = None

    @classmethod
    def leaf(cls, value: Fraction) -> "Expr":
        return cls(value=Fraction(value))

    @classmethod
    def binary(cls, op: str, left: "Expr", right: "Expr") -> "Expr":
        if op not in OPS:
            raise ValueError(f"unknown operator: {op}")
        return cls(op=op, left=left, right=right)

    @property
    def is_leaf(self) -> bool:
        return self.op is None

    @property
    def evaluated(self) -> Fraction:
        if self.is_leaf:
            assert self.value is not None
            return self.value
        assert self.left is not None and self.right is not None and self.op is not None
        left, right = self.left.evaluated, self.right.evaluated
        if self.op == "+":
            return left + right
        if self.op == "-":
            return left - right
        if self.op == "×":
            return left * right
        if right == 0:
            raise ZeroDivisionError("division by zero")
        return left / right

    @property
    def operator_count(self) -> int:
        if self.is_leaf:
            return 0
        assert self.left is not None and self.right is not None
        return 1 + self.left.operator_count + self.right.operator_count

    def render(self, parent_op: str | None = None, right_child: bool = False) -> str:
        if self.is_leaf:
            assert self.value is not None
            return format_fraction(self.value)

        assert self.left is not None and self.right is not None and self.op is not None
        left_text = self.left.render(self.op, False)
        right_text = self.right.render(self.op, True)
        text = f"{left_text} {self.op} {right_text}"

        if parent_op is None:
            return text
        current_precedence = PRECEDENCE[self.op]
        parent_precedence = PRECEDENCE[parent_op]
        need_parentheses = current_precedence < parent_precedence
        # A right child of the same precedence must keep its own operator when
        # it differs from the parent: a + (b - c), a - (b + c), and
        # a × (b ÷ c) cannot safely lose their parentheses.
        if right_child and current_precedence == parent_precedence:
            need_parentheses = self.op != parent_op or parent_op in ("-", "÷")
        if need_parentheses:
            return f"({text})"
        return text

    def canonical(self) -> str:
        if self.is_leaf:
            assert self.value is not None
            return f"N:{self.value.numerator}/{self.value.denominator}"
        assert self.left is not None and self.right is not None and self.op is not None
        left, right = self.left.canonical(), self.right.canonical()
        if self.op in ("+", "×") and left > right:
            left, right = right, left
        return f"({left}{self.op}{right})"

    def infix(self) -> str:
        return self.render() + " ="
