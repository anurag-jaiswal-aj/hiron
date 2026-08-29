import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from hiron.tenants.models import Tenant
from hiron.users.models import User, UserInvitationToken
from hiron.users.repository import UserInvitationTokenRepository, UserRepository

ADMIN_DB_URL = "postgresql+asyncpg://hiron_user:hiron_secure_password@localhost:5432/hiron_dev"


@pytest.fixture(scope="session")
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create a real PostgreSQL engine for integration tests."""
    engine = create_async_engine(ADMIN_DB_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture
async def setup_data(db_engine: AsyncEngine) -> AsyncGenerator[tuple[uuid.UUID, uuid.UUID], None]:
    """Setup test tenant and user in the database, with guaranteed cleanup."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        # Create Tenant
        tenant = Tenant(id=tenant_id, name="Test Tenant", slug=f"test-{tenant_id}")
        session.add(tenant)

        # Create User
        user = User(
            id=user_id,
            tenant_id=tenant_id,
            email=f"{user_id}@test.com",
            full_name="Integration User",
            password_hash="hash",
            role="org_admin",
        )
        session.add(user)
        await session.commit()

    try:
        yield tenant_id, user_id
    finally:
        # Guaranteed cleanup: Deleting the tenant cascades to User and UserInvitationToken
        async with async_session() as session:
            tenant_to_delete = await session.get(Tenant, tenant_id)
            if tenant_to_delete:
                await session.delete(tenant_to_delete)
                await session.commit()


@pytest.fixture
def invitation_repo() -> UserInvitationTokenRepository:
    """Fixture providing the token repository."""
    return UserInvitationTokenRepository()


@pytest.mark.asyncio
async def test_create_and_lookup_token(
    db_engine: AsyncEngine,
    invitation_repo: UserInvitationTokenRepository,
    setup_data: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Test token creation and lookup by hash."""
    _tenant_id, user_id = setup_data
    token_hash = "fakedb_hash_" + uuid.uuid4().hex
    expires = datetime.now(UTC) + timedelta(days=7)

    async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        token = UserInvitationToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires,
        )

        created = await invitation_repo.create(session, token)
        assert created.id is not None
        assert created.token_hash == token_hash
        assert created.used_at is None
        await session.commit()

    # Lookup
    async with async_session() as session:
        found = await invitation_repo.get_by_token_hash(session, token_hash)
        assert found is not None
        assert found.token_hash == token_hash


@pytest.mark.asyncio
async def test_token_hash_uniqueness(
    db_engine: AsyncEngine,
    invitation_repo: UserInvitationTokenRepository,
    setup_data: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Test that token_hash must be unique."""
    _tenant_id, user_id = setup_data
    token_hash = f"duplicate_hash_{uuid.uuid4().hex}"
    expires = datetime.now(UTC) + timedelta(days=7)

    async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        token1 = UserInvitationToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires,
        )
        await invitation_repo.create(session, token1)
        await session.commit()

    async with async_session() as session:
        token2 = UserInvitationToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires,
        )
        with pytest.raises(IntegrityError):
            await invitation_repo.create(session, token2)


@pytest.mark.asyncio
async def test_revoke_pending_for_user(
    db_engine: AsyncEngine,
    invitation_repo: UserInvitationTokenRepository,
    setup_data: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Test revoking all pending tokens for a user."""
    _tenant_id, user_id = setup_data

    async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        # Create two pending tokens
        for i in range(2):
            t = UserInvitationToken(
                user_id=user_id,
                token_hash=f"revoke_hash_{i}_{uuid.uuid4().hex}",
                expires_at=datetime.now(UTC) + timedelta(days=7),
            )
            await invitation_repo.create(session, t)

        await session.commit()

    # Verify pending
    async with async_session() as session:
        pending = await invitation_repo.get_pending_for_user(session, user_id)
        assert len(pending) >= 2

    # Revoke
    async with async_session() as session:
        revoked_count = await invitation_repo.revoke_pending_for_user(session, user_id)
        await session.commit()

        assert revoked_count >= 2

    # Verify none pending
    async with async_session() as session:
        pending_after = await invitation_repo.get_pending_for_user(session, user_id)
        assert len(pending_after) == 0


@pytest.mark.asyncio
async def test_atomic_consumption(
    db_engine: AsyncEngine,
    invitation_repo: UserInvitationTokenRepository,
    setup_data: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Test atomic marking of a token as used."""
    _tenant_id, user_id = setup_data
    token_hash = "atomic_hash_" + uuid.uuid4().hex

    async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        token = UserInvitationToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        await invitation_repo.create(session, token)
        await session.commit()

    # First consume should succeed
    async with async_session() as session:
        success = await invitation_repo.mark_used(session, token_hash)
        assert success is True
        await session.commit()

    # Verify used_at is set
    async with async_session() as session:
        found = await invitation_repo.get_by_token_hash(session, token_hash)
        assert found is not None
        assert found.used_at is not None

    # Second consume should fail
    async with async_session() as session:
        success2 = await invitation_repo.mark_used(session, token_hash)
        assert success2 is False


@pytest.mark.asyncio
async def test_user_deletion_cascades(
    db_engine: AsyncEngine,
    invitation_repo: UserInvitationTokenRepository,
    setup_data: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Test that deleting a user deletes their invitation tokens."""
    tenant_id, user_id = setup_data
    token_hash = "cascade_hash_" + uuid.uuid4().hex

    async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        token = UserInvitationToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        await invitation_repo.create(session, token)
        await session.commit()

    # Ensure token exists
    async with async_session() as session:
        found = await invitation_repo.get_by_token_hash(session, token_hash)
        assert found is not None

    # Delete user
    async with async_session() as session:
        user_repo = UserRepository()
        await user_repo.delete(session, user_id, tenant_id)
        await session.commit()

    # Verify token is deleted via CASCADE
    async with async_session() as session:
        found_after = await invitation_repo.get_by_token_hash(session, token_hash)
        assert found_after is None
