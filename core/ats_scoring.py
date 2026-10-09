
def normalize_items(value):
    """Convert comma/newline-separated text into normalized items."""
    return {
        item.strip().casefold()
        for item in value.replace("\n", ",").split(",")
        if item.strip()
    }


def calculate_ats_score(candidate, job):
    # 1. Skills score: 60%
    candidate_skills = normalize_items(candidate.skills)
    required_skills = normalize_items(job.skills)

    if required_skills:
        matched_skills = candidate_skills & required_skills
        skills_score = (
            len(matched_skills) / len(required_skills)
        ) * 100
    else:
        matched_skills = set()
        skills_score = None

    # 2. Experience score: 25%
    required_experience = job.experience_required

    if required_experience > 0:
        experience_score = min(
            candidate.experience / required_experience * 100,
            100
        )
    else:
        experience_score = 100

    # 3. Education score: 15%
    required_education = job.education_required.strip().casefold()
    candidate_education = candidate.education.strip().casefold()

    if required_education:
        education_score = (
            100
            if required_education in candidate_education
            else 0
        )
    else:
        education_score = None

    # Normalize weights when a criterion is not provided
    weighted_total = 0
    active_weight = 0

    if skills_score is not None:
        weighted_total += skills_score * 60
        active_weight += 60

    weighted_total += experience_score * 25
    active_weight += 25

    if education_score is not None:
        weighted_total += education_score * 15
        active_weight += 15

    match_percentage = round(weighted_total / active_weight, 2)

    return {
        "match_percentage": match_percentage,
        "skills_score": (
            round(skills_score, 2)
            if skills_score is not None else None
        ),
        "matched_skills": sorted(matched_skills),
        "missing_skills": sorted(required_skills - candidate_skills),
        "experience_score": round(experience_score, 2),
        "education_score": education_score,
    }