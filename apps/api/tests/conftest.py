"""Global pytest fixtures and model registry initialization for API tests."""

from hiron.ai_usage import models as _ai_usage_models
from hiron.audit import models as _audit_models
from hiron.candidates import models as _candidate_models
from hiron.embeddings import models as _embedding_models
from hiron.jobs import models as _job_models
from hiron.notes import models as _note_models
from hiron.pipeline import models as _pipeline_models
from hiron.resumes import models as _resume_models
from hiron.scores import models as _score_models
from hiron.search import models as _search_models
from hiron.tags import models as _tag_models
from hiron.tenants import models as _tenant_models
from hiron.tokens import models as _token_models
from hiron.users import models as _user_models

# Force SQLAlchemy Declarative Base model registration for isolated pytest collection
_DOMAIN_MODELS = (
    _ai_usage_models,
    _audit_models,
    _candidate_models,
    _embedding_models,
    _job_models,
    _note_models,
    _pipeline_models,
    _resume_models,
    _score_models,
    _search_models,
    _tag_models,
    _tenant_models,
    _token_models,
    _user_models,
)

import pytest
from hiron.core.config import get_settings

@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
