"""Tests for prompt registry."""

import pytest
from eval.prompts import list_prompts, load_prompt


class TestPromptRegistry:
    def test_list_pass1_prompts(self):
        """Should discover pass1_v1 prompt."""
        prompts = list_prompts(pass_number=1)
        assert "pass1_v1" in prompts

    def test_list_pass2_prompts(self):
        """Should discover pass2_v1 prompt."""
        prompts = list_prompts(pass_number=2)
        assert "pass2_v1" in prompts

    def test_load_pass1_prompt(self):
        """Should load system prompt and build function."""
        system_prompt, build_fn = load_prompt("pass1_v1")
        assert isinstance(system_prompt, str)
        assert len(system_prompt) > 100
        assert callable(build_fn)

    def test_build_pass1_message(self):
        """build_user_message should format posting into XML tags."""
        _, build_fn = load_prompt("pass1_v1")
        msg = build_fn(title="Field Rep", location="Atlanta, GA", full_text="Job description.")
        assert "<title>Field Rep</title>" in msg
        assert "<location>Atlanta, GA</location>" in msg
        assert "Job description." in msg

    def test_load_pass2_prompt(self):
        """Should load pass2 system prompt and build function."""
        system_prompt, build_fn = load_prompt("pass2_v1")
        assert "entity" in system_prompt.lower()
        assert callable(build_fn)

    def test_build_pass2_message(self):
        """Pass 2 build function takes content_role_specific as extra param."""
        _, build_fn = load_prompt("pass2_v1")
        msg = build_fn(
            title="Field Rep",
            location="Atlanta, GA",
            full_text="Full text here.",
            content_role_specific="Visit Best Buy stores.",
        )
        assert "Visit Best Buy stores." in msg

    def test_load_nonexistent_prompt_raises(self):
        """Should raise ImportError for unknown prompt version."""
        with pytest.raises(ImportError):
            load_prompt("pass1_v999")
