from __future__ import annotations

from compgraph.enrichment.prompts import (
    PASS2_SYSTEM_PROMPT,
    build_pass2_messages,
    build_pass2_user_message,
    sanitize_for_prompt,
)


class TestPass2PromptBoilerplateExclusion:
    def test_boilerplate_exclusion_section_present(self) -> None:
        assert "<boilerplate_exclusion>" in PASS2_SYSTEM_PROMPT
        assert "CRITICAL" in PASS2_SYSTEM_PROMPT

    def test_boilerplate_rule_in_rules_section(self) -> None:
        assert "boilerplate" in PASS2_SYSTEM_PROMPT.lower()
        assert "Do NOT include brands from company boilerplate" in PASS2_SYSTEM_PROMPT

    def test_osl_boilerplate_example_present(self) -> None:
        assert "OSL" in PASS2_SYSTEM_PROMPT
        assert "AT&T" in PASS2_SYSTEM_PROMPT or "AT&amp;T" in PASS2_SYSTEM_PROMPT

    def test_boilerplate_example_excludes_telco_brands(self) -> None:
        assert "Example 5" in PASS2_SYSTEM_PROMPT
        example_5_start = PASS2_SYSTEM_PROMPT.index("Example 5")
        example_5_end = PASS2_SYSTEM_PROMPT.index("Example 6", example_5_start)
        example_5 = PASS2_SYSTEM_PROMPT[example_5_start:example_5_end]
        assert "Walmart" in example_5
        assert "retailer" in example_5
        output_section = example_5[example_5.index("Output:") :]
        assert "AT&T" not in output_section
        assert "Verizon" not in output_section
        assert "T-Mobile" not in output_section

    def test_boilerplate_example_includes_role_specific_brand(self) -> None:
        assert "Example 6" in PASS2_SYSTEM_PROMPT
        example_6_start = PASS2_SYSTEM_PROMPT.index("Example 6")
        example_6 = PASS2_SYSTEM_PROMPT[example_6_start:]
        output_section = example_6[example_6.index("Output:") :]
        assert "Samsung" in output_section
        assert "client_brand" in output_section

    def test_prompt_instructs_focus_on_role_sections(self) -> None:
        assert "job TITLE" in PASS2_SYSTEM_PROMPT
        assert "RESPONSIBILITIES" in PASS2_SYSTEM_PROMPT
        assert "REQUIREMENTS" in PASS2_SYSTEM_PROMPT


class TestPass2UserMessage:
    def test_prefers_content_role_specific(self) -> None:
        msg = build_pass2_user_message(
            "Sales Rep",
            "Dallas, TX",
            "Visit Best Buy stores to promote Samsung.",
            "Full posting text with boilerplate about AT&T, Verizon...",
        )
        assert "Visit Best Buy" in msg
        assert "boilerplate" not in msg

    def test_falls_back_to_full_text(self) -> None:
        msg = build_pass2_user_message(
            "Sales Rep",
            "Dallas, TX",
            None,
            "Full text here.",
        )
        assert "Full text here." in msg

    def test_sanitizes_xml_characters(self) -> None:
        msg = build_pass2_user_message(
            "AT&T Rep",
            "Dallas <TX>",
            None,
            "Body with <script> & tags",
        )
        assert "&amp;" in msg
        assert "&lt;" in msg
        assert "&gt;" in msg


class TestPass2Messages:
    def test_returns_single_user_message(self) -> None:
        msgs = build_pass2_messages("Title", "Location", None, "Body")
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"


class TestSanitizeForPrompt:
    def test_escapes_ampersand_first(self) -> None:
        assert sanitize_for_prompt("A&B") == "A&amp;B"

    def test_escapes_angle_brackets(self) -> None:
        assert sanitize_for_prompt("<div>") == "&lt;div&gt;"

    def test_no_double_escape(self) -> None:
        assert sanitize_for_prompt("&lt;") == "&amp;lt;"
