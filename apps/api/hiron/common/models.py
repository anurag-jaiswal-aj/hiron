"""Declarative Base class, constraint naming conventions, and common abstract ORM model fields."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Constraint Naming Conventions per Engineering Guidelines §8 & Database Design
# ix: index, uq: unique, ck: check, fk: foreign key, pk: primary key
NAMING_CONVENTIONS = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Root Declarative Base class with explicit constraint naming conventions."""

    metadata = MetaData(naming_convention=NAMING_CONVENTIONS)


class BaseModel(Base):
    """Abstract base ORM model providing standard audit columns (id, created_at, updated_at).

    Per Database Design §9 & Engineering Guidelines §8:
    - id: UUIDv4 primary key generated automatically
    - created_at: TIMESTAMPTZ UTC timestamp on record insertion
    - updated_at: TIMESTAMPTZ UTC timestamp automatically updated on row modification
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        sort_order=-10,
        comment="Globally unique primary key identifier (UUIDv4)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        sort_order=100,
        comment="UTC timestamp when the record was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        sort_order=101,
        comment="UTC timestamp when the record was last updated",
    )
