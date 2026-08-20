import contextvars

# Context variable to hold the current tenant ID for the request lifecycle
tenant_context: contextvars.ContextVar[str | None] = contextvars.ContextVar("tenant_context", default=None)

def get_tenant_context() -> str | None:
    """Retrieve the current tenant ID from contextvars."""
    return tenant_context.get()

def set_tenant_context(tenant_id: str | None) -> None:
    """Set the current tenant ID in contextvars."""
    tenant_context.set(tenant_id)
