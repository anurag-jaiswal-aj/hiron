"""Candidate Management domain package."""

from hiron.candidates.exceptions import (
    CandidateNotFoundError,
    DuplicateCandidateEmailError,
    InsufficientCandidatePermissionsError,
    InvalidCandidateDataError,
    JobCandidateConflictError,
)
from hiron.candidates.models import Candidate, JobCandidate
from hiron.candidates.repository import CandidateRepository
from hiron.candidates.router import jobs_candidate_router, router as candidates_router
from hiron.candidates.service import CandidateService

__all__ = [
    "Candidate",
    "CandidateNotFoundError",
    "CandidateRepository",
    "CandidateService",
    "DuplicateCandidateEmailError",
    "InsufficientCandidatePermissionsError",
    "InvalidCandidateDataError",
    "JobCandidate",
    "JobCandidateConflictError",
    "candidates_router",
    "jobs_candidate_router",
]
