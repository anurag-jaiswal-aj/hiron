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
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pathlib import Path
from hiron.core.config import get_settings
from hiron.core.jwt import load_private_key, load_public_key


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def session_rsa_keys(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """Generate ephemeral RSA 2048-bit keys exactly once per test session."""
    private_key_obj = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = private_key_obj.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = private_key_obj.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    keys_dir = tmp_path_factory.mktemp("keys")
    priv_file = keys_dir / "test_rsa_private.pem"
    pub_file = keys_dir / "test_rsa_public.pem"
    priv_file.write_bytes(priv_pem)
    pub_file.write_bytes(pub_pem)

    return priv_file, pub_file


@pytest.fixture(autouse=True)
def inject_jwt_keys(
    session_rsa_keys: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inject ephemeral keys into the fresh Settings instance and clear JWT caches for every test."""
    priv_file, pub_file = session_rsa_keys
    settings = get_settings()

    monkeypatch.setattr(settings, "jwt_private_key_path", str(priv_file))
    monkeypatch.setattr(settings, "jwt_public_key_path", str(pub_file))

    load_private_key.cache_clear()
    load_public_key.cache_clear()
