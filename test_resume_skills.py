from django.test import SimpleTestCase

from core.resume_parser import (
    extract_resume_skills,
    extract_experience_years,
    extract_education,
    parse_resume_data,
)


class ResumeSkillsTests(SimpleTestCase):

    def setUp(self):
        self.sample_text = """
        Python Developer

        Skills: Python, Django, SQL, HTML, CSS, Git

        Professional Experience:
        3 years of experience in Python development.

        Education:
        Bachelor in Computer Science
        MBA
        """

    def test_extract_resume_skills(self):
        skills = extract_resume_skills(self.sample_text)

        self.assertIn("Python", skills)
        self.assertIn("Django", skills)
        self.assertIn("SQL", skills)

    def test_extract_experience_years(self):
        experience = extract_experience_years(self.sample_text)

        self.assertEqual(experience, [3])

    def test_extract_education(self):
        education = extract_education(self.sample_text)

        self.assertIn("MBA", education)
        self.assertIn("Bachelor", education)

    def test_parse_resume_data(self):
        resume_data = parse_resume_data(self.sample_text)

        self.assertIn("Python", resume_data["skills"])
        self.assertEqual(resume_data["experience_years"], [3])
        self.assertIn("MBA", resume_data["education"])
