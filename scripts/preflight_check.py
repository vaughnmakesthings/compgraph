#!/usr/bin/env python3
"""Thin CLI wrapper for compgraph.preflight.

Usage:
    uv run python scripts/preflight_check.py [--fix] [--json] [--checks python,tools]
"""

import sys

from compgraph.preflight import main

if __name__ == "__main__":
    sys.exit(main())
