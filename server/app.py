"""OpenEnv-compliant server entry point."""
from __future__ import annotations

import uvicorn

# Re-export the FastAPI app from the root module
import sys
from pathlib import Path

# Ensure the project root is on the path so `env` and `baseline` imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app  # noqa: E402


def main(host: str = "0.0.0.0", port: int = 7860):
    """Start the GitTangle server."""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
