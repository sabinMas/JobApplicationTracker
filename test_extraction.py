"""Test the profile extraction directly."""
import asyncio
import sys
sys.path.insert(0, 'backend')

from backend.app.services.ai_service import extract_profile

test_resume = """
JANE DOE
San Francisco, CA
jane@example.com | (555) 123-4567
linkedin.com/in/janedoe | github.com/janedoe | janedoe.dev

PROFESSIONAL SUMMARY
Full-stack engineer with 5+ years building cloud-native applications.
Expertise in Python, TypeScript, and AWS infrastructure.

SKILLS
Python, TypeScript, React, FastAPI, AWS, PostgreSQL, Docker, Kubernetes,
Machine Learning, API Design, System Architecture

EXPERIENCE
Senior Software Engineer | TechCorp | Jan 2022 - Present
- Led migration of monolith to microservices, reducing deployment time by 60%
- Designed and implemented real-time data pipeline processing 1M+ events/day
- Mentored 3 junior engineers, improving team velocity by 40%

Software Engineer | StartupXYZ | Jun 2019 - Dec 2021
- Built full-stack web application with React and FastAPI, used by 50k+ users
- Implemented CI/CD pipeline using GitHub Actions, reducing release cycle to 2 hours
- Optimized database queries resulting in 3x performance improvement

EDUCATION
M.S. Computer Science | UC Berkeley | 2019
B.S. Computer Science | UC Davis | 2017

CERTIFICATIONS
AWS Certified Solutions Architect - Associate | 2020
Kubernetes Application Developer (CKAD) | 2021
"""

async def test():
    result = await extract_profile(test_resume)
    print("Extracted Profile:")
    print(f"  Name: {result.get('full_name')}")
    print(f"  Email: {result.get('email')}")
    print(f"  Summary: {result.get('summary')[:100] if result.get('summary') else 'EMPTY'}")
    print(f"  Skills ({len(result.get('skills', []))}):")
    for skill in result.get('skills', [])[:5]:
        print(f"    - {skill}")
    print(f"  Experience ({len(result.get('experience', []))}):")
    for exp in result.get('experience', []):
        print(f"    - {exp.get('title')} @ {exp.get('company')}")
    print(f"  Education ({len(result.get('education', []))}):")
    for edu in result.get('education', []):
        print(f"    - {edu.get('degree')} in {edu.get('field')} from {edu.get('school')}")
    print(f"  Certifications ({len(result.get('certifications', []))}):")
    for cert in result.get('certifications', []):
        print(f"    - {cert.get('name')}")

asyncio.run(test())
