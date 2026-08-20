"""Unit tests for the Vercel serverless entrypoint."""

from unittest.mock import patch


def test_vercel_entrypoint_loads_successfully() -> None:
    """Verify that importing the Vercel entrypoint exports the configured FastAPI app without starting a server."""

    # Ensure uvicorn.run is completely prevented from running, even if there was a mistake
    with patch("uvicorn.run") as mock_run:
        import sys
        from pathlib import Path
        root_dir = Path(__file__).resolve().parent.parent.parent.parent
        sys.path.insert(0, str(root_dir))

        # Import the entrypoint dynamically to ensure it runs during the test
        import api.index as vercel_entrypoint
        from fastapi import FastAPI
        assert isinstance(vercel_entrypoint.app, FastAPI)

        # Verify routes are registered (in newer FastAPI they are _IncludedRouter instances)
        assert len(vercel_entrypoint.app.routes) > 10

        # Verify uvicorn.run was NEVER called during import
        assert not mock_run.called
