
# core/report_service.py

from django.core.exceptions import ObjectDoesNotExist

from .models import Application, ATSScore


def generate_candidate_report(application_id):
    try:
        application = (
            Application.objects
            .select_related("candidate__user", "job")
            .get(id=application_id)
        )
    except Application.DoesNotExist:
        return None

    # ATS evaluation
    ats = ATSScore.objects.filter(
        application=application
    ).first()

    if ats:
        ats_score = ats.match_percentage
        matched_skills = ats.matched_skills or []
        missing_skills = ats.missing_skills or []
    else:
        ats_score = None
        matched_skills = []
        missing_skills = []

    # Latest AI call status
    latest_call = application.ai_call_logs.order_by(
        "-created_at"
    ).first()

    ai_call_status = latest_call.status if latest_call else None

    # Scores from completed AI interview sessions
    sessions = (
        application.ai_interview_sessions
        .filter(status="COMPLETED")
        .prefetch_related("questions__answer")
    )

    answer_scores = []

    for session in sessions:
        for question in session.questions.all():
            try:
                answer = question.answer
            except ObjectDoesNotExist:
                continue

            answer_scores.append(answer.total_score)

    if answer_scores:
        ai_interview_score = round(
            sum(answer_scores) / len(answer_scores), 2
        )
    else:
        ai_interview_score = None

    # Evidence-based strengths and risks
    strengths = []
    risks = []

    if matched_skills:
        strengths.append(
            "Matched skills: " + ", ".join(matched_skills)
        )

    if missing_skills:
        risks.append(
            "Missing required skills: "
            + ", ".join(missing_skills)
        )

    if ats_score is None:
        risks.append("ATS score is not available.")

    if ai_interview_score is None:
        risks.append("Completed AI interview evaluation is not available.")

    return {
        "application_id": application.id,
        "candidate": application.candidate.user.username,
        "job_title": application.job.title,
        "application_status": application.status,
        "ats_score": ats_score,
        "ai_call_status": ai_call_status,
        "ai_interview_score": ai_interview_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "strengths": strengths,
        "risks": risks,
    }
