"""Random valid expression generation with canonical duplicate removal."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import random

from expression import Expr, OPS
from fraction_utils import format_fraction


@dataclass(frozen=True)
class GeneratedProblem:
    expression: Expr

    @property
    def question(self) -> str:
        return self.expression.infix()

    @property
    def answer(self) -> str:
        return format_fraction(self.expression.evaluated)


def random_operand(rng: random.Random, limit: int) -> Fraction:
    """Generate an integer or proper fraction with all components < limit."""
    if limit <= 1 or rng.random() < 0.58:
        return Fraction(rng.randrange(limit), 1)
    denominator = rng.randrange(2, limit)
    numerator = rng.randrange(1, denominator)
    return Fraction(numerator, denominator)


def make_candidate(rng: random.Random, limit: int, operators: int) -> Expr:
    if operators == 0:
        return Expr.leaf(random_operand(rng, limit))

    left_ops = rng.randrange(operators)
    right_ops = operators - 1 - left_ops
    left = make_candidate(rng, limit, left_ops)
    right = make_candidate(rng, limit, right_ops)
    op = rng.choice(OPS)
    if op == "-" and left.evaluated < right.evaluated:
        left, right = right, left
    if op == "÷" and (right.evaluated == 0 or not (Fraction(0) < left.evaluated / right.evaluated < Fraction(1))):
        raise ValueError("division is not a positive proper fraction")
    candidate = Expr.binary(op, left, right)
    if candidate.evaluated < 0:
        raise ValueError("negative intermediate result")
    return candidate


def generate_problems(count: int, limit: int, seed: int | None = None) -> list[GeneratedProblem]:
    if count < 1:
        raise ValueError("题目数量必须为正整数")
    if limit < 2:
        raise ValueError("-r 必须至少为 2，且所有数值/分母都小于该范围")

    rng = random.Random(seed)
    problems: list[GeneratedProblem] = []
    seen: set[str] = set()
    attempts = 0
    max_attempts = max(10000, count * 300)
    while len(problems) < count and attempts < max_attempts:
        attempts += 1
        try:
            candidate = make_candidate(rng, limit, rng.randint(1, 3))
        except (ValueError, ZeroDivisionError):
            continue
        key = candidate.canonical()
        if key in seen:
            continue
        seen.add(key)
        problems.append(GeneratedProblem(candidate))

    if len(problems) != count:
        raise RuntimeError(
            f"在范围 {limit} 内最多生成 {len(problems)} 道不重复题目，无法满足 {count} 道请求；请增大 -r"
        )
    return problems
