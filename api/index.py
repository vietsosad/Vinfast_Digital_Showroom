import sys
from pathlib import Path

# The application package lives under backend/src. Vercel imports this adapter
# from the repository root, so expose backend as the Python import root.
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from src.main import app

# Export ASGI app for Vercel Serverless Handler
__all__ = ["app"]
