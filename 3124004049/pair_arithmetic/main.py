"""Command-line entry point for the paired arithmetic project."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from generator import generate_problems
from grader import grade_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="小学四则运算题目生成与自动批改程序")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-n", type=int, help="生成题目数量")
    group.add_argument("-e", metavar="EXERCISES", help="题目文件")
    parser.add_argument("-r", type=int, help="数值和分母范围上界（不含）")
    parser.add_argument("-a", metavar="ANSWERS", help="学生答案文件")
    parser.add_argument("--seed", type=int, default=None, help="可选随机种子，便于复现测试")
    return parser


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.n is not None:
            if args.r is None:
                parser.error("生成模式必须同时提供 -r")
            if args.a is not None:
                parser.error("生成模式不能使用 -a")
            problems = generate_problems(args.n, args.r, args.seed)
            Path("Exercises.txt").write_text("\n".join(p.question for p in problems) + "\n", encoding="utf-8")
            Path("Answers.txt").write_text("\n".join(p.answer for p in problems) + "\n", encoding="utf-8")
            print(f"已生成 {len(problems)} 道题目。")
            print("题目文件：Exercises.txt")
            print("答案文件：Answers.txt")
            return 0

        if args.r is not None or args.a is None:
            parser.error("批改模式必须同时提供 -e 和 -a，且不能使用 -r")
        result = grade_files(args.e, args.a)
        Path("Grade.txt").write_text(result.report(), encoding="utf-8")
        print(result.report(), end="")
        print("批改结果已写入 Grade.txt")
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(run())
