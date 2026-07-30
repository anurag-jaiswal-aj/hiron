"""Unit tests for AIScoringEngine dimensional evaluation, cosine similarity integration, and hallucination checks."""

from hiron.candidates.models import Candidate
from hiron.jobs.models import Job
from hiron.scores.engine import AIScoringEngine


def test_cosine_similarity_calculation() -> None:
    """Verify cosine similarity calculation between vectors."""
    engine = AIScoringEngine()
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [1.0, 0.0, 0.0]
    assert engine.compute_cosine_similarity(vec_a, vec_b) == 1.0

    vec_c = [0.0, 1.0, 0.0]
    assert engine.compute_cosine_similarity(vec_a, vec_c) == 0.0


def test_skills_matching_calculation() -> None:
    """Verify skills matched vs missing and dimension score calculation."""
    engine = AIScoringEngine()
    candidate = Candidate(full_name="Jane Doe", skills=["Python", "FastAPI", "Docker"])
    job = Job(
        title="Backend Dev",
        description="Python dev",
        required_skills=["Python", "FastAPI", "Kubernetes"],
    )

    matched, missing, score = engine.calculate_skills_matching(candidate, job)

    assert "Python" in matched
    assert "FastAPI" in matched
    assert "Kubernetes" in missing
    assert score == 67  # 2/3 = ~67%


def test_scoring_engine_full_evaluation() -> None:
    """Verify full evaluation produces complete score payload."""
    engine = AIScoringEngine()
    candidate = Candidate(
        full_name="Jane Smith",
        summary="Senior Software Engineer with 8 years of Python experience",
        skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        total_experience_years=8,
    )
    job = Job(
        title="Senior Python Engineer",
        description="Looking for senior Python developer with 5+ years experience",
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        experience_years_min=5,
    )

    result = engine.evaluate(candidate, job)

    assert 0 <= result["fit_score"] <= 100
    assert 0.0 <= result["confidence"] <= 1.0
    assert "skills" in result["breakdown"]
    assert "experience" in result["breakdown"]
    assert "education" in result["breakdown"]
    assert "Jane Smith" in result["explanation"]
    assert "Python" in result["skills_matched"]
    assert result["prompt_version"] == "2.0.0"
