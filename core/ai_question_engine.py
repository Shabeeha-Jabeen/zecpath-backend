
from core.models import Job, QuestionTemplate, JobQuestionMapping


def get_questions_for_job(job_id):
    """
    Return questions configured for a job.
    If no questions are mapped, return active general questions.
    """
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        return {
            "success": False,
            "message": "Job not found.",
            "questions": [],
        }

    mapped_questions = QuestionTemplate.objects.filter(
        job_mappings__job=job,
        is_active=True,
    ).distinct().order_by(
        "job_mappings__order"
    )

    if not mapped_questions.exists():
        mapped_questions = QuestionTemplate.objects.filter(
            role="ALL",
            is_active=True,
        ).order_by("id")

    questions = [
        {
            "id": question.id,
            "question_text": question.question_text,
            "category": question.category,
            "role": question.role,
        }
        for question in mapped_questions
    ]

    return {
        "success": True,
        "job_id": job.id,
        "job_title": job.title,
        "total_questions": len(questions),
        "questions": questions,
    }

def get_follow_up_question(answer_text):
    """
    Select a follow-up question based on the candidate's answer.
    """
    if not answer_text or not answer_text.strip():
        return {
            "category": "SKILLS",
            "question_text": "Could you tell me more about your technical skills?",
        }

    answer = answer_text.lower()

    if "python" in answer:
        return {
            "category": "SKILLS",
            "question_text": "How much experience do you have with Django?",
        }

    if "no experience" in answer or "beginner" in answer:
        return {
            "category": "EXPERIENCE",
            "question_text": "What programming concepts have you learned so far?",
        }

    return {
        "category": "EXPERIENCE",
        "question_text": "Could you describe your relevant experience in more detail?",
    }

