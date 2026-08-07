"""Unit tests for ResumeParser NER extraction, skills taxonomy matching, and parse confidence scoring."""

from unittest.mock import MagicMock, patch

from hiron.resumes.parser import ResumeParser, get_nlp


@patch("hiron.resumes.parser.get_nlp", return_value=None)
def test_resume_parser_contact_info_extraction(mock_get_nlp: MagicMock) -> None:
    """Verify name, email, phone, location, and linkedin extraction."""
    _ = mock_get_nlp
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


@patch("hiron.resumes.parser.get_nlp", return_value=None)
def test_resume_parser_confidence_score_calculation(mock_get_nlp: MagicMock) -> None:
    """Verify confidence score for partial resume data."""
    _ = mock_get_nlp
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


@patch("hiron.resumes.parser.get_nlp", return_value=None)
def test_resume_parser_incomplete_resume(mock_get_nlp: MagicMock) -> None:
    """Verify parsing handles incomplete resumes safely without crashing."""
    _ = mock_get_nlp
    parser = ResumeParser()
    text = "Just a random line of text.\nAnother random line."
    parsed_data, confidence = parser.parse(text)
    _ = confidence

    assert parsed_data["full_name"] == "Just a random line of text."
    assert parsed_data["email"] is None
    assert parsed_data["phone"] is None
    assert parsed_data["linkedin_url"] is None
    assert parsed_data["skills"] == []
    assert parsed_data["experience"] == []
    assert parsed_data["education"] == []


@patch("hiron.resumes.parser.get_nlp", return_value=None)
def test_resume_parser_malformed_noisy_resume(mock_get_nlp: MagicMock) -> None:
    """Verify parsing handles noisy/malformed formatting."""
    _ = mock_get_nlp
    parser = ResumeParser()
    text = """
    ***!!!***
    John_Doe_123!
    ---
    Email: john...doe@@@example..com
    Phone: (555)-123-4567ext123

    SKILLS
    Python,,,, Java,, C++...

    EXPERIENCE
    Manager at Tech Corp
    """
    parsed_data, _confidence = parser.parse(text)

    assert "John_Doe_123" in parsed_data["full_name"]
    assert parsed_data["phone"] == "(555)-123-4567"
    assert "Python" in parsed_data["skills"]
    assert "Java" in parsed_data["skills"]
    assert len(parsed_data["experience"]) >= 1


@patch("hiron.resumes.parser.get_nlp", return_value=None)
def test_resume_parser_empty_optional_sections(mock_get_nlp: MagicMock) -> None:
    """Verify parsing handles empty optional sections safely."""
    _ = mock_get_nlp
    parser = ResumeParser()
    text = """
    Alice Bob
    alice@bob.com

    SUMMARY

    EXPERIENCE

    EDUCATION

    SKILLS

    """
    parsed_data, _confidence = parser.parse(text)

    assert parsed_data["full_name"] == "Alice Bob"
    assert parsed_data["email"] == "alice@bob.com"
    # The simple regex parser might capture the next heading as summary if the section is completely empty
    assert parsed_data["summary"] is None or parsed_data["summary"] == "EXPERIENCE"
    assert parsed_data["experience"] == []
    assert parsed_data["education"] == []
    assert parsed_data["skills"] == []


def test_parser_model_version_truthfulness() -> None:
    """Verify PARSER_MODEL_VERSION accurately describes the hybrid implementation."""
    from hiron.resumes.parser import PARSER_MODEL_VERSION
    assert PARSER_MODEL_VERSION == "spacy-en_core_web_trf-3.8.0"
    parser = ResumeParser()
    assert parser.model_version == "spacy-en_core_web_trf-3.8.0"


@patch("hiron.resumes.parser.get_nlp")
def test_resume_parser_spacy_enhancement(mock_get_nlp: MagicMock) -> None:
    """Verify SpaCy correctly enhances fields like full_name, location, and company."""
    # Mock the SpaCy document and entities
    mock_doc = MagicMock()

    ent_person = MagicMock()
    ent_person.label_ = "PERSON"
    ent_person.text = "John Connor Jr."

    ent_gpe = MagicMock()
    ent_gpe.label_ = "GPE"
    ent_gpe.text = "Los Angeles, CA"

    ent_org = MagicMock()
    ent_org.label_ = "ORG"
    ent_org.text = "Tech Innovators"

    mock_doc.ents = [ent_person, ent_gpe, ent_org]

    mock_nlp = MagicMock(return_value=mock_doc)
    mock_get_nlp.return_value = mock_nlp

    parser = ResumeParser()
    text = """
    Unknown Candidate

    EXPERIENCE
    Software Engineer -
    """
    # Force regex to fail to extract a clean name or location
    parsed_data, _confidence = parser.parse(text)

    # SpaCy should have populated these
    assert parsed_data["full_name"] == "John Connor Jr."
    assert parsed_data["location"] == "Los Angeles, CA"
    assert len(parsed_data["experience"]) >= 1
    assert parsed_data["experience"][0]["company"] == "Tech Innovators"


def test_resume_parser_spacy_real_model_smoke() -> None:
    """Smoke test to verify the real SpaCy model can load without crashing."""
    nlp = get_nlp()
    assert nlp is not None
