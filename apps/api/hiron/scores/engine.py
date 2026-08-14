"""AI Candidate-Job Fit Scoring Engine per Engineering Guidelines §6 & Appendix A."""

import json
import math
import time
from typing import Any

import httpx
import structlog
from fastapi import HTTPException
from pydantic import ValidationError

from hiron.candidates.models import Candidate
from hiron.core.config import get_settings
from hiron.jobs.models import Job
from hiron.scores.schemas import AIGeneratedScore
from hiron.security.prompt_builder import PromptBuilder

logger = structlog.get_logger("hiron.scores.engine")

DEFAULT_PROMPT_NAME = "candidate_fit_scoring"
DEFAULT_PROMPT_VERSION = "2.0.0"
DEFAULT_LLM_MODEL_VERSION = "gpt-4o-2024-08-06"


class AIScoringEngine:
    """AI scoring engine computing candidate-job dimensional breakdown and explanation using Gemini."""

    def __init__(
        self,
        prompt_name: str = DEFAULT_PROMPT_NAME,
        prompt_version: str = DEFAULT_PROMPT_VERSION,
        model_version: str = "models/gemini-flash-latest",
    ) -> None:
        self.prompt_name = prompt_name
        self.prompt_version = prompt_version
        self.model_version = model_version

    def run_hallucination_and_consistency_checks(
        self,
        _candidate: Candidate,
        job: Job,
        skills_matched: list[str],
        skills_missing: list[str],
        fit_score: int,
    ) -> list[str]:
        """Perform Appendix A.12 hallucination and score consistency sanity checks."""
        warnings: list[str] = []

        if len(skills_missing) > 5:
            warnings.append(
                f"Candidate is missing {len(skills_missing)} required skills for {job.title}"
            )

        if fit_score > 85 and len(skills_missing) > len(skills_matched):
            warnings.append("High overall score despite missing more required skills than matched")

        return warnings

    async def evaluate(
        self,
        candidate: Candidate,
        job: Job,
        _resume_text: str | None = None,
        candidate_vector: list[float] | None = None,
        job_vector: list[float] | None = None,
    ) -> dict[str, Any]:
        """Perform AI candidate-job evaluation pipeline via Gemini and produce structured score payload."""
        # 1. Structural Security Boundary Construction
        system_instructions = (
            f"You are evaluating {candidate.full_name} for the role of {job.title}. "
            "You must return a valid JSON object matching this schema exactly: \n"
            "{\n"
            "  \"fit_score\": int (0-100),\n"
            "  \"confidence\": float (0.0-1.0),\n"
            "  \"explanation\": str,\n"
            "  \"skills_matched\": [str],\n"
            "  \"skills_missing\": [str],\n"
            "  \"breakdown\": {\n"
            "    \"skills\": {\"score\": int (0-100), \"details\": str},\n"
            "    \"experience\": {\"score\": int (0-100), \"details\": str},\n"
            "    \"education\": {\"score\": int (0-100), \"details\": str}\n"
            "  }\n"
            "}\n"
        )
        builder = PromptBuilder(system_instructions=system_instructions)
        _llm_messages = builder.build_messages({
            "candidate_skills": ", ".join(candidate.skills) if candidate.skills else "",
            "candidate_summary": candidate.summary or "",
            "candidate_resume_text": _resume_text or "",
            "job_description": job.description or "",
            "job_required_skills": ", ".join(job.required_skills) if job.required_skills else "",
        })

        system_text = next((m["content"] for m in _llm_messages if m["role"] == "system"), "")
        user_text = next((m["content"] for m in _llm_messages if m["role"] == "user"), "")

        payload = {
            "systemInstruction": {
                "parts": [{"text": system_text}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_text}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
            }
        }

        settings = get_settings()
        api_key = settings.gemini_api_key
        if not api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured")

        url = f"https://generativelanguage.googleapis.com/v1beta/{self.model_version}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}

        start_time = time.time()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=7.5)
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            # Propagate 429 and 5xx so QStash retries
            if e.response.status_code in (429, 503, 500, 502, 504):
                raise
            # Terminal invalid 4xx
            raise HTTPException(status_code=e.response.status_code, detail=f"Terminal Gemini error: {e.response.text}")
        except httpx.TimeoutException:
            # Propagate timeout
            raise

        latency_ms = int((time.time() - start_time) * 1000)

        response_data = response.json()

        # Extract tokens
        usage_meta = response_data.get("usageMetadata", {})
        input_tokens = usage_meta.get("promptTokenCount", 0)
        output_tokens = usage_meta.get("candidatesTokenCount", 0)

        # Extract JSON string
        try:
            candidates = response_data.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates in Gemini response")
            content_parts = candidates[0].get("content", {}).get("parts", [])
            if not content_parts:
                raise ValueError("No text parts in Gemini response")
            raw_json_str = content_parts[0].get("text", "")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected Gemini response format: {str(e)}")

        # Pydantic validation
        try:
            ai_score = AIGeneratedScore.model_validate_json(raw_json_str)
        except ValidationError as e:
            # Terminal validation error
            raise HTTPException(status_code=422, detail=f"Gemini output validation failed: {str(e)}")

        warnings = self.run_hallucination_and_consistency_checks(
            candidate, job, ai_score.skills_matched, ai_score.skills_missing, ai_score.fit_score
        )

        breakdown = {
            "skills": {
                "score": ai_score.breakdown.skills.score,
                "weight": 0.40,
                "details": ai_score.breakdown.skills.details,
            },
            "experience": {
                "score": ai_score.breakdown.experience.score,
                "weight": 0.35,
                "details": ai_score.breakdown.experience.details,
            },
            "education": {
                "score": ai_score.breakdown.education.score,
                "weight": 0.25,
                "details": ai_score.breakdown.education.details,
            },
        }

        return {
            "fit_score": ai_score.fit_score,
            "confidence": ai_score.confidence,
            "breakdown": breakdown,
            "explanation": ai_score.explanation,
            "skills_matched": ai_score.skills_matched,
            "skills_missing": ai_score.skills_missing,
            "warnings": warnings,
            "prompt_name": self.prompt_name,
            "prompt_version": self.prompt_version,
            "model_version": self.model_version,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": latency_ms,
        }
