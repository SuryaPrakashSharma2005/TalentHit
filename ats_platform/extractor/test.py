from services.resume_service import process_resume

job_requirements = {
    "skills": ["python", "fastapi", "sql"],
    "min_experience": 1.0,
    "degree": "B.TECH"
}

result = process_resume(
    resume_path="Resume prince testing .pdf",
    job_requirements=job_requirements
)

print("FINAL ATS OUTPUT:")
for k, v in result.items():
    print(f"\n{k.upper()}:")
    print(v)
