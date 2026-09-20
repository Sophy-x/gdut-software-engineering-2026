"""Answer-file grading and report formatting."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fraction_utils import parse_number
from parser import parse_answer, parse_expression


@dataclass(frozen=True)
class GradeResult:
    correct: tuple[int, ...]
    wrong: tuple[int, ...]

    def report(self) -> str:
        correct_ids = ", ".join(map(str, self.correct))
        wrong_ids = ", ".join(map(str, self.wrong))
        return (
            f"Correct: {len(self.correct)} ({correct_ids})\n\n"
            f"Wrong: {len(self.wrong)} ({wrong_ids})\n"
        )


def grade_files(exercises_path: str | Path, answers_path: str | Path) -> GradeResult:
    exercises = Path(exercises_path).read_text(encoding="utf-8-sig").splitlines()
    answers = Path(answers_path).read_text(encoding="utf-8-sig").splitlines()
    correct: list[int] = []
    wrong: list[int] = []
    for index, exercise in enumerate(exercises, start=1):
        try:
            expected = parse_expression(exercise).evaluated
            actual = parse_answer(answers[index - 1]) if index <= len(answers) else None
            if actual == expected:
                correct.append(index)
            else:
                wrong.append(index)
        except (ValueError, ZeroDivisionError, IndexError):
            wrong.append(index)
    return GradeResult(tuple(correct), tuple(wrong))
