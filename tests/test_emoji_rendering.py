"""Tests for emoji rendering — Unicode characters, not shortcodes."""

from compgraph.dashboard.queries import FRESHNESS_ICONS


class TestFreshnessIcons:
    def test_icons_are_unicode_not_shortcodes(self):
        for key, icon in FRESHNESS_ICONS.items():
            assert not icon.startswith(":"), f"FRESHNESS_ICONS['{key}'] is a shortcode: {icon}"

    def test_all_colors_present(self):
        assert set(FRESHNESS_ICONS.keys()) == {"green", "yellow", "red", "gray"}
