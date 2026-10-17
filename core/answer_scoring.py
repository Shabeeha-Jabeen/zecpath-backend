from core.models import AIAnswer
def calculate_keyword_score(answer_text, expected_keywords):
    """
    Calculate keyword matching score from 0 to 100.
    """
    if not expected_keywords:
        return 100.0

    answer = (answer_text or "").lower()

    matched_keywords = [
        keyword
        for keyword in expected_keywords
        if keyword.lower() in answer
    ]

    score = (len(matched_keywords) / len(expected_keywords)) * 100

    return round(score, 2)


def calculate_completeness_score(answer_text, minimum_words=10):
    """
    Calculate a basic completeness score from 0 to 100.
    """
    words = (answer_text or "").split()

    if not words:
        return 0.0

    score = min(len(words) / minimum_words, 1) * 100

    return round(score, 2)


def calculate_relevance_score(answer_text, expected_keywords):
    """
    Estimate relevance using expected keyword matching.
    """
    return calculate_keyword_score(answer_text, expected_keywords)


def calculate_total_score(
    relevance_score,
    completeness_score,
    keyword_score,
):
    """
    Calculate a weighted score from 0 to 100.
    """
    total = (
        relevance_score * 0.40
        + completeness_score * 0.30
        + keyword_score * 0.30
    )

    return round(max(0, min(total, 100)), 2)


def evaluate_and_save_answer(
    answer_id,
    expected_keywords,
    confidence_score=None,
    ai_annotations=None,
):
    """
    Calculate evaluation scores and save them to AIAnswer.
    Scores are heuristic estimates, not real AI judgments.
    """
    answer_obj = AIAnswer.objects.get(id=answer_id)

    answer_text = answer_obj.answer_text or ""

    keyword_score = calculate_keyword_score(
        answer_text,
        expected_keywords,
    )

    completeness_score = calculate_completeness_score(
        answer_text,
    )

    relevance_score = calculate_relevance_score(
        answer_text,
        expected_keywords,
    )

    total_score = calculate_total_score(
        relevance_score,
        completeness_score,
        keyword_score,
    )

    answer_obj.confidence_score = confidence_score
    answer_obj.ai_annotations = ai_annotations or {}
    answer_obj.keyword_score = keyword_score
    answer_obj.completeness_score = completeness_score
    answer_obj.relevance_score = relevance_score
    answer_obj.total_score = total_score

    answer_obj.save(
        update_fields=[
            "confidence_score",
            "ai_annotations",
            "keyword_score",
            "completeness_score",
            "relevance_score",
            "total_score",
        ]
    )

    return {
        "answer_id": answer_obj.id,
        "relevance_score": relevance_score,
        "completeness_score": completeness_score,
        "keyword_score": keyword_score,
        "total_score": total_score,
        "confidence_score": confidence_score,
        "ai_annotations": answer_obj.ai_annotations,
    }
