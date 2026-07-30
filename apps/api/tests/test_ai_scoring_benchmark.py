"""AI Candidate Scoring Benchmark evaluation test per Phase 17."""

from unittest.mock import MagicMock

from hiron.scores.engine import AIScoringEngine


def test_ai_scoring_engine_evaluation_benchmark() -> None:
    """Verify AI scoring engine calculates dimensional sub-scores and overall fit score."""
    engine = AIScoringEngine()

    mock_candidate = MagicMock(
        full_name="Alice Candidate",
        skills=["Python", "FastAPI", "PostgreSQL"],
        total_experience_years=5,
        summary="Bachelor of Science in Computer Science.",
    )
    mock_job = MagicMock(
        title="Backend Engineer",
        required_skills=["Python", "FastAPI"],
        experience_years_min=3,
    )

    eval_result = engine.evaluate(
        candidate=mock_candidate,
        job=mock_job,
        candidate_vector=[0.1] * 1536,
        job_vector=[0.1] * 1536,
    )

    assert 0 <= eval_result["fit_score"] <= 100
    assert "skills" in eval_result["breakdown"]
    assert "experience" in eval_result["breakdown"]
    assert "education" in eval_result["breakdown"]
    assert eval_result["explanation"] is not None


def test_cosine_similarity_calculation() -> None:
    """Verify vector cosine similarity computation."""
    engine = AIScoringEngine()

    vec_a = [1.0, 0.0, 0.0]
    vec_b = [1.0, 0.0, 0.0]

    sim = engine.compute_cosine_similarity(vec_a, vec_b)
    assert sim == 1.0

    ortho_sim = engine.compute_cosine_similarity([1.0, 0.0], [0.0, 1.0])
    assert ortho_sim == 0.0
