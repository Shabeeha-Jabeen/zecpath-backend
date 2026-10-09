from core.resume_parser import (
    extract_resume_skills,
    extract_experience_years,
    extract_education,
    parse_resume_data,
)
import json

sample_text = """
Python Developer

Skills: Python, Django, SQL, HTML, CSS, Git

Professional Experience:
3 years of experience in Python development.

Education:
Bachelor in Computer Science
MBA
"""

skills = extract_resume_skills(sample_text)
experience = extract_experience_years(sample_text)
education = extract_education(sample_text)

print("Extracted Skills:", skills)
print("Experience Years:", experience)
print("Education:", education)

resume_data = parse_resume_data(sample_text)

print("\nStructured Resume JSON:")
print(json.dumps(resume_data, indent=4))