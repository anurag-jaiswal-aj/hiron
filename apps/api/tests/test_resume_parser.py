"""Unit tests for ResumeParser NER extraction, skills taxonomy matching, and parse confidence scoring."""

from hiron.resumes.parser import PARSER_MODEL_VERSION, ResumeParser


def test_resume_parser_contact_info_extraction() -> None:
    """Verify name, email, phone, location, and linkedin extraction."""
    parser = ResumeParser()
    sample_resume_text = """
    Sarah Connor
    sarah.connor@cyberdyne.com | +1 (555) 019-2831 | San Francisco, CA
    https://linkedin.com/in/sarahconnor

    SUMMARY
    Experienced lead systems engineer with 8 years of experience building resilient cloud systems.

    EXPERIENCE
    Lead Engineer at Cyberdyne Systems
    Senior Developer at Skynet

    EDUCATION
    B.S. Computer Science, UC Berkeley, 2018

    SKILLS
    Python, FastAPI, Docker, Kubernetes, PostgreSQL, AWS, React, C++
    """

    parsed_data, confidence = parser.parse(sample_resume_text)

    assert parsed_data["full_name"] == "Sarah Connor"
    assert parsed_data["email"] == "sarah.connor@cyberdyne.com"
    assert parsed_data["phone"] == "+1 (555) 019-2831"
    assert parsed_data["location"] == "San Francisco, CA"
    assert parsed_data["linkedin_url"] == "https://linkedin.com/in/sarahconnor"
    assert "Python" in parsed_data["skills"]
    assert "FastAPI" in parsed_data["skills"]
    assert "Kubernetes" in parsed_data["skills"]
    assert len(parsed_data["experience"]) >= 1
    assert len(parsed_data["education"]) >= 1
    assert confidence == 1.0
    assert parser.model_version == PARSER_MODEL_VERSION


def test_resume_parser_confidence_score_calculation() -> None:
    """Verify confidence score for partial resume data."""
    parser = ResumeParser()

    full_data = {
        "full_name": "Jane Smith",
        "email": "jane@example.com",
        "skills": ["Python"],
        "experience": [{"title": "Engineer"}],
    }
    assert parser.calculate_confidence(full_data) == 1.0

    partial_data = {
        "full_name": "Parsed Candidate",
        "email": "jane@example.com",
        "skills": [],
        "experience": [],
    }
    assert parser.calculate_confidence(partial_data) == 0.25
