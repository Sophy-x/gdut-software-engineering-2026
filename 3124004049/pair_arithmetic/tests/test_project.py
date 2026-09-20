from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import tempfile
import unittest

from expression import Expr
from fraction_utils import format_fraction, parse_number
from generator import generate_problems
from grader import grade_files
from parser import parse_answer, parse_expression


class FractionTests(unittest.TestCase):
    def test_parse_and_format(self) -> None:
        self.assertEqual(parse_number("2’3/8"), Fraction(19, 8))
        self.assertEqual(parse_number("2'3/8"), Fraction(19, 8))
        self.assertEqual(format_fraction(Fraction(23, 24)), "23/24")
        self.assertEqual(format_fraction(Fraction(19, 8)), "2’3/8")


class ExpressionTests(unittest.TestCase):
    def test_exact_evaluation(self) -> None:
        expr = parse_expression("1/6 + 1/8")
        self.assertEqual(expr.evaluated, Fraction(7, 24))

    def test_commutative_duplicates_have_same_key(self) -> None:
        self.assertEqual(
            parse_expression("23 + 45").canonical(),
            parse_expression("45 + 23").canonical(),
        )
        self.assertEqual(
            parse_expression("3 + (2 + 1)").canonical(),
            parse_expression("1 + 2 + 3").canonical(),
        )
        self.assertNotEqual(
            parse_expression("1 + 2 + 3").canonical(),
            parse_expression("3 + 2 + 1").canonical(),
        )

    def test_parser_rejects_trailing_garbage(self) -> None:
        with self.assertRaises(ValueError):
            parse_expression("1 + 2 ???")

    def test_render_preserves_same_precedence_right_child(self) -> None:
        original = Expr.binary(
            "+",
            Expr.leaf(Fraction(8)),
            Expr.binary("-", Expr.leaf(Fraction(5)), Expr.leaf(Fraction(3))),
        )
        self.assertEqual(original.render(), "8 + (5 - 3)")
        self.assertEqual(parse_expression(original.render()).evaluated, original.evaluated)


class GeneratorTests(unittest.TestCase):
    def assert_valid_tree(self, expr: Expr, limit: int) -> None:
        if expr.is_leaf:
            assert expr.value is not None
            self.assertLess(expr.value.numerator, limit * expr.value.denominator)
            return
        assert expr.left is not None and expr.right is not None and expr.op is not None
        self.assert_valid_tree(expr.left, limit)
        self.assert_valid_tree(expr.right, limit)
        if expr.op == "-":
            self.assertGreaterEqual(expr.left.evaluated, expr.right.evaluated)
        if expr.op == "÷":
            self.assertGreater(expr.evaluated, 0)
            self.assertLess(expr.evaluated, 1)

    def test_generation_constraints(self) -> None:
        problems = generate_problems(300, 20, seed=42)
        self.assertEqual(len({p.expression.canonical() for p in problems}), 300)
        for problem in problems:
            self.assertLessEqual(problem.expression.operator_count, 3)
            self.assertGreaterEqual(problem.expression.evaluated, 0)
            self.assert_valid_tree(problem.expression, 20)

    def test_generated_question_round_trip(self) -> None:
        for problem in generate_problems(100, 10, seed=7):
            question = problem.question.removesuffix(" =")
            self.assertEqual(parse_expression(question).evaluated, problem.expression.evaluated)

    def test_large_generation(self) -> None:
        problems = generate_problems(10000, 10, seed=42)
        self.assertEqual(len(problems), 10000)


class GraderTests(unittest.TestCase):
    def test_grade_mixed_answers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            exercises = root / "Exercises.txt"
            answers = root / "Answers.txt"
            exercises.write_text("1 + 2 =\n1/2 + 1/2 =\n8 - 3 =\n", encoding="utf-8")
            answers.write_text("3\n2/2\n9\n", encoding="utf-8")
            result = grade_files(exercises, answers)
            self.assertEqual(result.correct, (1, 2))
            self.assertEqual(result.wrong, (3,))

    def test_missing_answer_is_wrong(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Exercises.txt").write_text("1 + 2 =\n", encoding="utf-8")
            (root / "Answers.txt").write_text("", encoding="utf-8")
            self.assertEqual(grade_files(root / "Exercises.txt", root / "Answers.txt").wrong, (1,))


if __name__ == "__main__":
    unittest.main()
