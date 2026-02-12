"""Allow running with `python -m compgraph` or `uv run compgraph`."""

import uvicorn

from compgraph.config import settings


def main():
    uvicorn.run(
        "compgraph.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=(settings.ENVIRONMENT == "dev"),
    )


if __name__ == "__main__":
    main()
