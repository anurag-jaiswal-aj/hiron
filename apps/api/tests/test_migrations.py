"""Real migration smoke test verifying Alembic upgrade head and downgrade base execution."""

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import OperationalError

from alembic import command
from hiron.core.config import get_settings


def test_alembic_migration_upgrade_and_downgrade_smoke() -> None:
    """Smoke test executing real Alembic upgrade head and downgrade base.

    Verifies:
    1. Upgrade head creates the 'tenants' table.
    2. Downgrade base drops the 'tenants' table cleanly.
    """
    root_dir = Path(__file__).resolve().parents[1]
    alembic_ini_path = root_dir / "alembic.ini"

    assert alembic_ini_path.exists(), "alembic.ini must exist at apps/api/alembic.ini"

    settings = get_settings()
    # Convert asyncpg URL to psycopg/psycopg2 sync URL for Alembic sync inspector test
    sync_db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")

    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)

    engine = create_engine(sync_db_url)

    try:
        # Test DB connectivity before running full migration smoke test
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
    except (OperationalError, Exception):
        pytest.skip(
            "PostgreSQL test database connection not available; skipping live migration smoke test."
        )

    try:
        # 1. Execute upgrade head
        command.upgrade(alembic_cfg, "head")

        # 2. Verify 'tenants' table exists
        inspector = inspect(engine)
        tables_after_upgrade = inspector.get_table_names()
        assert "tenants" in tables_after_upgrade, "tenants table must exist after upgrade head"

        # 3. Execute downgrade base
        command.downgrade(alembic_cfg, "base")

        # 4. Verify 'tenants' table was cleanly removed
        inspector = inspect(engine)
        tables_after_downgrade = inspector.get_table_names()
        assert (
            "tenants" not in tables_after_downgrade
        ), "tenants table must not exist after downgrade base"

    finally:
        engine.dispose()
