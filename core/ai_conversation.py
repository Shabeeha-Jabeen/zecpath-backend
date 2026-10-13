
from django.utils import timezone

from .models import AIInterviewSession, AIQuestion, AIAnswer, CallLog


def save_transcript(session_id, transcript_text, transcript_json=None):
    """Save the transcript for an AI interview session."""
    session = AIInterviewSession.objects.get(id=session_id)

    session.transcript_text = transcript_text
    session.transcript_json = transcript_json or {}
    session.updated_at = timezone.now()
    session.save(
        update_fields=[
            "transcript_text",
            "transcript_json",
            "updated_at",
        ]
    )

    return session


def save_question_and_answer(
    session_id,
    question_text,
    answer_text,
    order=1,
    structured_data=None,
):
    """Save an interview question and its answer."""
    session = AIInterviewSession.objects.get(id=session_id)

    question = AIQuestion.objects.create(
        session=session,
        question_text=question_text,
        order=order,
        asked_at=timezone.now(),
    )

    answer = AIAnswer.objects.create(
        question=question,
        answer_text=answer_text,
        transcript_text=answer_text,
        structured_data=structured_data or {},
        answered_at=timezone.now(),
    )

    return question, answer


def create_call_audit_log(
    event_type,
    triggered_by=None,
    session=None,
    call_log=None,
    reason="",
    details=None,
):
    """Record who triggered an AI call, when, and why."""
    return CallLog.objects.create(
        event_type=event_type,
        triggered_by=triggered_by,
        session=session,
        call_log=call_log,
        reason=reason,
        details=details or {},
    )
