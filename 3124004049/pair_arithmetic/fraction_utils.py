"""Exact fraction parsing and formatting for the arithmetic exercise project."""

from __future__ import annotations

from fractions import Fraction
import re


MIXED_MARKS = "'’"


def parse_number(text: str) -> Fraction:
    """Parse an integer, proper fraction, or mixed number into Fraction."""
    value = text.strip().replace(" ", "")
    if not value:
        raise ValueError("empty number")

    mixed = re.fullmatch(r"(\d+)[\u0027\u2019](\d+)/(\d+)", value)
    if mixed:
        whole, numerator, denominator = map(int, mixed.groups())
        if denominator == 0 or numerator >= denominator:
            raise ValueError(f"invalid mixed number: {text}")
        return Fraction(whole * denominator + numerator, denominator)

    proper = re.fullmatch(r"(\d+)/(\d+)", value)
    if proper:
        numerator, denominator = map(int, proper.groups())
        if denominator == 0:
            raise ValueError("division by zero")
        return Fraction(numerator, denominator)

    if re.fullmatch(r"\d+", value):
        return Fraction(int(value), 1)
    raise ValueError(f"invalid number: {text}")


def format_fraction(value: Fraction) -> str:
    """Use the assignment's integer / a/b / a’b/c notation."""
    value = Fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    if value.numerator < value.denominator:
        return f"{value.numerator}/{value.denominator}"
    whole, remainder = divmod(value.numerator, value.denominator)
    return f"{whole}’{remainder}/{value.denominator}"
