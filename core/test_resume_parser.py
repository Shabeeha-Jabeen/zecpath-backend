
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile

from core.resume_parser import extract_resume_text, clean_resume_text


# Test text cleaning
sample_text = "  Shabeeha Jabeen  \n\n  Python Developer  "

cleaned_text = clean_resume_text(sample_text)

print("Cleaned text:")
print(cleaned_text)


# Test DOCX extraction using a temporary document
from docx import Document

document = Document()
document.add_paragraph("Shabeeha Jabeen")
document.add_paragraph("Python Django Developer")

docx_buffer = BytesIO()
document.save(docx_buffer)

docx_file = SimpleUploadedFile(
    "sample_resume.docx",
    docx_buffer.getvalue(),
    content_type=(
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    ),
)

extracted_text = extract_resume_text(docx_file)

print("\nExtracted DOCX text:")
print(extracted_text)