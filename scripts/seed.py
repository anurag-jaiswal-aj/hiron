#!/usr/bin/env python3
"""Database seeding script to provision initial tenant organization and org_admin user."""

import asyncio
import os
import sys
from pathlib import Path

# Add apps/api to Python path for module resolution
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "apps" / "api"))

# Import all ORM models to register mapper relationships with SQLAlchemy registry
import hiron.candidates.models
import hiron.embeddings.models
import hiron.jobs.models
import hiron.notes.models
import hiron.resumes.models
import hiron.scores.models
import hiron.tags.models
import hiron.tenants.models
import hiron.tokens.models
import hiron.users.models  # noqa: F401
from hiron.core.database import AsyncSessionLocal, engine
from hiron.tenants.service import TenantService
from hiron.users.service import UserService


async def seed_database() -> None:
    """Seed the database with initial tenant and org_admin user if empty."""
    tenant_name = os.getenv("TENANT_NAME", "Acme Corp")
    tenant_slug = os.getenv("TENANT_SLUG", "acme")
    admin_name = os.getenv("ADMIN_NAME", "Admin User")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@acme.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "SecurePassword123!")

    tenant_service = TenantService()
    user_service = UserService()

    async with AsyncSessionLocal() as session:
        try:
            # Idempotency check: verify if any tenant already exists
            existing_tenants = await tenant_service.list_active_tenants(session, limit=1)
            if existing_tenants:
                tenant = existing_tenants[0]
            else:
                # Atomic provisioning of initial tenant
                tenant = await tenant_service.create_tenant(
                    session=session,
                    name=tenant_name,
                    slug=tenant_slug,
                    plan="enterprise",
                )

            from hiron.users.repository import UserRepository
            user_repo = UserRepository()

            # Ensure org_admin
            admin_user = await user_repo.get_by_email_and_tenant(session, admin_email, tenant.id)
            if not admin_user:
                admin_user = await user_service.create_user(
                    session=session,
                    tenant_id=tenant.id,
                    email=admin_email,
                    full_name=admin_name,
                    role="org_admin",
                    password=admin_password,
                )

            # Ensure recruiter
            recruiter_user = await user_repo.get_by_email_and_tenant(session, "recruiter@acme.com", tenant.id)
            if not recruiter_user:
                recruiter_user = await user_service.create_user(
                    session=session,
                    tenant_id=tenant.id,
                    email="recruiter@acme.com",
                    full_name="Recruiter User",
                    role="recruiter",
                    password=admin_password,
                )

            # Ensure hiring_manager
            manager_user = await user_repo.get_by_email_and_tenant(session, "manager@acme.com", tenant.id)
            if not manager_user:
                manager_user = await user_service.create_user(
                    session=session,
                    tenant_id=tenant.id,
                    email="manager@acme.com",
                    full_name="Hiring Manager User",
                    role="hiring_manager",
                    password=admin_password,
                )

            await session.commit()

            print("✓ Database seeding completed successfully.")
            print(f"  Tenant ID:   {tenant.id}")
            print(f"  Tenant Name: {tenant.name} ({tenant.slug})")
            print(f"  Admin User:  {admin_user.full_name} <{admin_user.email}>")
            print(f"  Recruiter:   {recruiter_user.full_name} <{recruiter_user.email}>")
            print(f"  Manager:     {manager_user.full_name} <{manager_user.email}>")

        except Exception as exc:
            await session.rollback()
            print(f"❌ Database seeding failed: {exc}", file=sys.stderr)
            sys.exit(1)
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_database())
