"""Auto-discovering prompt registry.

Scans this directory for pass{N}_*.py files. Each module must export:
- SYSTEM_PROMPT: str
- build_user_message: Callable[..., str]
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from pathlib import Path


def list_prompts(pass_number: int) -> list[str]:
    """Return available prompt version names for a given pass."""
    prompts_dir = Path(__file__).parent
    prefix = f"pass{pass_number}_"
    return sorted(p.stem for p in prompts_dir.glob(f"{prefix}*.py") if not p.name.startswith("_"))


def load_prompt(version: str) -> tuple[str, Callable]:
    """Load a prompt module by version name.

    Returns (SYSTEM_PROMPT, build_user_message) tuple.
    Raises ImportError if the module doesn't exist.
    """
    mod = importlib.import_module(f"eval.prompts.{version}")
    return mod.SYSTEM_PROMPT, mod.build_user_message
