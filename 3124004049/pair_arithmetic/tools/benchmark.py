"""Measure the assignment's 10,000-question generation requirement."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from generator import generate_problems


def main() -> None:
    started = perf_counter()
    problems = generate_problems(10_000, 10, seed=42)
    elapsed = perf_counter() - started
    unique = len({problem.expression.canonical() for problem in problems})
    print(f"generated={len(problems)}")
    print(f"unique={unique}")
    print(f"elapsed_seconds={elapsed:.4f}")


if __name__ == "__main__":
    main()
