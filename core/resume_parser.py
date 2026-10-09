
import re
from pathlib import Path
import pdfplumber
from docx import Document


def extract_resume_text(file):
    """
    Extract text from a PDF or DOCX resume.
    """
    file_extension = Path(file.name).suffix.lower()

    if file_extension == ".pdf":
        text_parts = []

        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()

                if page_text:
                    text_parts.append(page_text)

        text = "\n".join(text_parts)

    elif file_extension == ".docx":
        document = Document(file)

        paragraphs = [
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]

        text = "\n".join(paragraphs)

    else:
        raise ValueError(
            "Unsupported file format. Upload a PDF or DOCX file."
        )

    return text


def clean_resume_text(text):
    """
    Clean extra spaces and unwanted formatting.
    """
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)

    return text.strip()


SKILLS_LIBRARY = [
    "Python",
    "Django",
    "Django REST Framework",
    "SQL",
    "PostgreSQL",
    "SQLite",
    "HTML",
    "CSS",
    "JavaScript",
    "React",
    "Bootstrap",
    "Git",
    "GitHub",
    "REST API",
]


def extract_resume_skills(text):
    """
    Extract predefined skills from resume text.
    """
    found_skills = []

    for skill in SKILLS_LIBRARY:
        pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"

        if re.search(pattern, text, re.IGNORECASE):
            found_skills.append(skill)

    return found_skills


def extract_experience_years(text):
    """
    Extract explicit experience duration and estimate duration
    from common month-year date ranges.
    """
    explicit_pattern = r"(\d+)\+?\s+years?\s+(?:of\s+)?experience"
    explicit_matches = re.findall(
        explicit_pattern, text, re.IGNORECASE
    )

    if explicit_matches:
        return [int(year) for year in explicit_matches]

    date_pattern = (
        r"\b(Jan|January|Feb|February|Mar|March|Apr|April|May|"
        r"Jun|June|Jul|July|Aug|August|Sep|September|Oct|October|"
        r"Nov|November|Dec|December)\s+(\d{4})\s*[-–—]\s*"
        r"(Jan|January|Feb|February|Mar|March|Apr|April|May|"
        r"Jun|June|Jul|July|Aug|August|Sep|September|Oct|October|"
        r"Nov|November|Dec|December)\s+(\d{4})\b"
    )

    matches = re.findall(date_pattern, text, re.IGNORECASE)

    if not matches:
        return []

    month_numbers = {
        "jan": 1, "january": 1,
        "feb": 2, "february": 2,
        "mar": 3, "march": 3,
        "apr": 4, "april": 4,
        "may": 5,
        "jun": 6, "june": 6,
        "jul": 7, "july": 7,
        "aug": 8, "august": 8,
        "sep": 9, "september": 9,
        "oct": 10, "october": 10,
        "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }

    durations = []

    for start_month, start_year, end_month, end_year in matches:
        start = int(start_year) * 12 + month_numbers[start_month.lower()]
        end = int(end_year) * 12 + month_numbers[end_month.lower()]

        if end >= start:
            months = end - start + 1
            durations.append(round(months / 12, 2))

    return durations

def extract_education(text):
    """
    Identify common education qualifications in resume text.
    """
    qualifications = [
        "PhD",
        "Master's",
        "MBA",
        "MCA",
        "B.Tech",
        "B.E.",
        "B.Sc",
        "B.Com",
        "B.A.",
        "Bachelor",
        "Diploma",
        "Plus Two",
    ]

    found_education = []

    for qualification in qualifications:
        pattern = re.escape(qualification)

        if re.search(pattern, text, re.IGNORECASE):
            found_education.append(qualification)

    return found_education

def parse_resume_data(text):
    """
    Convert extracted resume information into structured data.
    """
    cleaned_text = clean_resume_text(text)

    return {
        "skills": extract_resume_skills(cleaned_text),
        "experience_years": extract_experience_years(cleaned_text),
        "education": extract_education(cleaned_text),
        "cleaned_text": cleaned_text,
    }