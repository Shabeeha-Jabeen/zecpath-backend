import os
import sys

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
from core.answer_scoring import (
    calculate_keyword_score,
    calculate_completeness_score,
    calculate_relevance_score,
    calculate_total_score,
)


def test_keyword_score():
    score = calculate_keyword_score(
        "I know Python and Django",
        ["Python", "Django", "SQL"],
    )
    assert score == 66.67


def test_empty_keyword_score():
    score = calculate_keyword_score("", [])
    assert score == 100.0


def test_completeness_score():
    score = calculate_completeness_score(
        "I know Python Django and SQL very well"
    )
    print("Completeness score:", score)
    assert score == 80.0
def test_empty_completeness_score():
    assert calculate_completeness_score("") == 0.0


def test_relevance_score():
    score = calculate_relevance_score(
        "I know Python",
        ["Python", "Django"],
    )
    assert score == 50.0


def test_total_score():
    score = calculate_total_score(80, 60, 100)
    assert score == 80.0


if __name__ == "__main__":
    test_keyword_score()
    test_empty_keyword_score()
    test_completeness_score()
    test_empty_completeness_score()
    test_relevance_score()
    test_total_score()
    print("All answer scoring tests passed!")
