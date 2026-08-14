"""AI Candidate Scoring Benchmark evaluation test per Phase 17."""

import json
import math
from pathlib import Path
from unittest.mock import MagicMock

from hiron.embeddings.generator import EMBEDDING_DIMENSION
from hiron.scores.engine import AIScoringEngine


def pearson_correlation(x: list[float], y: list[float]) -> float:
    """Calculate the Pearson Correlation Coefficient (r) between two arrays."""
    n = len(x)
    if n == 0:
        return 0.0

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    denominator = math.sqrt(
        sum((xi - mean_x) ** 2 for xi in x) * sum((yi - mean_y) ** 2 for yi in y)
    )

    if denominator == 0:
        return 0.0

    return numerator / denominator


def test_ai_scoring_engine_evaluation_benchmark() -> None:
    """Verify AI scoring engine distribution and confidence correlation on 100 candidates."""
    engine = AIScoringEngine()

    # Target Job Mock (Standard Backend Engineer)
    mock_job = MagicMock(
        title="Backend Engineer",
        required_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        experience_years_min=3,
        description="Backend engineering role requiring Python and database expertise.",
    )
    # The job vector will be ones to easily compute cosine similarity against candidates
    job_vector = [1.0] * EMBEDDING_DIMENSION

    # Load 100 candidates fixture
    fixture_path = Path(__file__).parent / "fixtures" / "candidates_100.json"
    with open(fixture_path, "r") as f:
        candidates_data = json.load(f)

    assert len(candidates_data) == 100

    results = []
    completeness_scores = []
    confidence_scores = []

    for c_data in candidates_data:
        mock_candidate = MagicMock(
            full_name=c_data["full_name"],
            skills=c_data["skills"],
            total_experience_years=c_data["total_experience_years"],
            summary=c_data["summary"],
        )

        # Pad the mock vector to EMBEDDING_DIMENSION dimensions by repeating the core
        core_vector = c_data["mock_vector_core"]
        candidate_vector = (core_vector * (EMBEDDING_DIMENSION // len(core_vector) + 1))[:EMBEDDING_DIMENSION]

        eval_result = engine.evaluate(
            candidate=mock_candidate,
            job=mock_job,
            candidate_vector=candidate_vector,
            job_vector=job_vector,
        )

        results.append(eval_result)
        completeness_scores.append(float(c_data["data_completeness_score"]))
        confidence_scores.append(float(eval_result["confidence"]))

    # 1. Assert Distribution Spread Requirements (Not all 90+, Not all < 50)
    fit_scores = [r["fit_score"] for r in results]
    assert any(s >= 90 for s in fit_scores), "Expected at least one score >= 90"
    assert not all(s >= 90 for s in fit_scores), "Expected not ALL scores to be >= 90"

    assert any(s < 50 for s in fit_scores), "Expected at least one score < 50"
    assert not all(s < 50 for s in fit_scores), "Expected not ALL scores to be < 50"

    # 2. Assert Confidence Correlation Requirement
    # Pearson Correlation Coefficient (r) should be strongly positive
    r_value = pearson_correlation(completeness_scores, confidence_scores)

    # Print the r_value for the test report output
    print(f"\nAI Benchmark Results:")
    print(f"Min Fit Score: {min(fit_scores)}")
    print(f"Max Fit Score: {max(fit_scores)}")
    print(f"Pearson Correlation (Completeness vs Confidence): {r_value:.4f}")

    assert r_value > 0.5, f"Expected strong positive correlation (>0.5), got {r_value:.4f}"


def test_cosine_similarity_calculation() -> None:
    """Verify vector cosine similarity computation."""
    engine = AIScoringEngine()

    vec_a = [1.0, 0.0, 0.0]
    vec_b = [1.0, 0.0, 0.0]

    sim = engine.compute_cosine_similarity(vec_a, vec_b)
    assert sim == 1.0

    ortho_sim = engine.compute_cosine_similarity([1.0, 0.0], [0.0, 1.0])
    assert ortho_sim == 0.0
