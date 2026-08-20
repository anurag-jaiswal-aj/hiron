"""Unit tests for AIScoringEngine Gemini REST integration and validation."""

from unittest.mock import patch

import httpx
import pytest

from hiron.candidates.models import Candidate
from hiron.jobs.models import Job
from hiron.scores.engine import AIScoringEngine


@pytest.fixture
def sample_candidate() -> Candidate:
    return Candidate(
        full_name="Jane Smith",
        summary="Senior Software Engineer with 8 years of Python experience",
        skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        total_experience_years=8,
    )


@pytest.fixture
def sample_job() -> Job:
    return Job(
        title="Senior Python Engineer",
        description="Looking for senior Python developer with 5+ years experience",
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        experience_years_min=5,
    )


@pytest.fixture(autouse=True)
def setup_gemini_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")
    from hiron.core.config import get_settings
    get_settings.cache_clear()


@pytest.fixture
def valid_gemini_response() -> dict:
    return {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": """{
                                "fit_score": 92,
                                "confidence": 0.85,
                                "explanation": "Excellent fit for the role.",
                                "skills_matched": ["Python", "FastAPI", "PostgreSQL"],
                                "skills_missing": [],
                                "breakdown": {
                                    "skills": {"score": 100, "details": "All required skills met."},
                                    "experience": {"score": 95, "details": "Exceeds 5 years."},
                                    "education": {"score": 80, "details": "Adequate."}
                                }
                            }"""
                        }
                    ]
                }
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 150,
            "candidatesTokenCount": 50
        }
    }


@pytest.mark.asyncio
@patch("hiron.scores.engine.httpx.AsyncClient.post")
async def test_scoring_engine_success(mock_post, sample_candidate, sample_job, valid_gemini_response) -> None:
    """Verify valid Gemini response is correctly parsed into ScoreData structure."""
    from unittest.mock import MagicMock
    mock_response = MagicMock()
    mock_response.json.return_value = valid_gemini_response
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    engine = AIScoringEngine()
    result = await engine.evaluate(sample_candidate, sample_job)

    assert result["fit_score"] == 92
    assert result["confidence"] == 0.85
    assert result["breakdown"]["skills"]["score"] == 100
    assert result["breakdown"]["skills"]["weight"] == 0.40
    assert result["explanation"] == "Excellent fit for the role."
    assert result["input_tokens"] == 150
    assert result["output_tokens"] == 50
    assert result["latency_ms"] >= 0

    # Verify timeout constraint
    kwargs = mock_post.call_args.kwargs
    assert kwargs.get("timeout") == 7.5


@pytest.mark.asyncio
@patch("hiron.scores.engine.httpx.AsyncClient.post")
async def test_scoring_engine_429_propagation(mock_post, sample_candidate, sample_job) -> None:
    """Verify HTTP 429 bubbles up as httpx.HTTPStatusError for QStash to retry."""
    mock_response = httpx.Response(429, request=httpx.Request("POST", "url"))
    mock_post.side_effect = httpx.HTTPStatusError("429 Too Many Requests", request=mock_response.request, response=mock_response)

    engine = AIScoringEngine()
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await engine.evaluate(sample_candidate, sample_job)

    assert exc_info.value.response.status_code == 429


@pytest.mark.asyncio
@patch("hiron.scores.engine.httpx.AsyncClient.post")
async def test_scoring_engine_5xx_propagation(mock_post, sample_candidate, sample_job) -> None:
    """Verify HTTP 500 bubbles up as httpx.HTTPStatusError for QStash to retry."""
    mock_response = httpx.Response(500, request=httpx.Request("POST", "url"))
    mock_post.side_effect = httpx.HTTPStatusError("500 Internal Server Error", request=mock_response.request, response=mock_response)

    engine = AIScoringEngine()
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await engine.evaluate(sample_candidate, sample_job)

    assert exc_info.value.response.status_code == 500


@pytest.mark.asyncio
@patch("hiron.scores.engine.httpx.AsyncClient.post")
async def test_scoring_engine_timeout_propagation(mock_post, sample_candidate, sample_job) -> None:
    """Verify httpx.TimeoutException bubbles up for QStash to retry."""
    mock_post.side_effect = httpx.TimeoutException("Read timeout")

    engine = AIScoringEngine()
    with pytest.raises(httpx.TimeoutException):
        await engine.evaluate(sample_candidate, sample_job)


@pytest.mark.asyncio
@patch("hiron.scores.engine.httpx.AsyncClient.post")
async def test_scoring_engine_malformed_json_terminal(mock_post, sample_candidate, sample_job) -> None:
    """Verify malformed JSON results in terminal HTTPException 422."""
    malformed_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": '{"fit_score": "not_an_int"}'
                        }
                    ]
                }
            }
        ]
    }

    from unittest.mock import MagicMock
    mock_response = MagicMock()
    mock_response.json.return_value = malformed_response
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    from pydantic import ValidationError
    engine = AIScoringEngine()
    with pytest.raises(ValidationError):
        await engine.evaluate(sample_candidate, sample_job)
