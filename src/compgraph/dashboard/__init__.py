"""CompGraph Dashboard package."""

import logging


def configure_logging() -> None:
    """Configure structured logging for the dashboard. Safe to call multiple times."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("compgraph.dashboard").setLevel(logging.DEBUG)
