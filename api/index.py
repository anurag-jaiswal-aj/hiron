import sys
from pathlib import Path

# Add the apps/api directory to sys.path so that absolute imports (e.g., `from hiron...`) resolve correctly
api_dir = Path(__file__).resolve().parent.parent / "apps" / "api"
sys.path.insert(0, str(api_dir))

# Import the FastAPI application instance
from hiron.main import app

# Export the app instance for the @vercel/python builder
__all__ = ["app"]
