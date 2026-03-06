"""Tests for the proxy provider system (ProxyProvider, StaticProxyProvider,
OxylabsProvider, ProxyPool, get_proxy_client_kwargs)."""

from __future__ import annotations

import pytest

from compgraph.scrapers.proxy import (
    _USER_AGENTS,
    OxylabsProvider,
    ProxyPool,
    ProxyProvider,
    StaticProxyProvider,
    get_proxy_client_kwargs,
    random_user_agent,
)

# ---------------------------------------------------------------------------
# ProxyProvider protocol conformance
# ---------------------------------------------------------------------------


class TestProxyProviderProtocol:
    """Verify StaticProxyProvider and OxylabsProvider satisfy the Protocol."""

    def test_static_satisfies_protocol(self) -> None:
        provider = StaticProxyProvider("http://proxy.example.com:8080")
        assert isinstance(provider, ProxyProvider)

    def test_oxylabs_satisfies_protocol(self) -> None:
        provider = OxylabsProvider(username="user", password="pass")
        assert isinstance(provider, ProxyProvider)


# ---------------------------------------------------------------------------
# StaticProxyProvider
# ---------------------------------------------------------------------------


class TestStaticProxyProvider:
    @pytest.mark.asyncio
    async def test_returns_configured_url(self) -> None:
        provider = StaticProxyProvider("http://myproxy.example.com:3128")
        url = await provider.get_proxy_url("icims.com")
        assert url == "http://myproxy.example.com:3128"

    @pytest.mark.asyncio
    async def test_domain_agnostic(self) -> None:
        """StaticProxyProvider ignores the domain arg."""
        provider = StaticProxyProvider("http://proxy.example.com")
        assert await provider.get_proxy_url("icims.com") == await provider.get_proxy_url(
            "workday.com"
        )

    def test_report_success_resets_failure_count(self) -> None:
        provider = StaticProxyProvider("http://p.example.com")
        provider.report_failure("icims.com")
        provider.report_failure("icims.com")
        provider.report_success("icims.com")
        assert provider._failures.get("icims.com", 0) == 0

    def test_report_failure_increments_count(self) -> None:
        provider = StaticProxyProvider("http://p.example.com")
        provider.report_failure("icims.com")
        provider.report_failure("icims.com")
        assert provider._failures["icims.com"] == 2


# ---------------------------------------------------------------------------
# OxylabsProvider
# ---------------------------------------------------------------------------


class TestOxylabsProvider:
    def test_url_format_basic(self) -> None:
        provider = OxylabsProvider(username="myuser", password="mypass")
        url = provider._build_url("icims.com")
        assert "myuser-country-us" in url
        assert "mypass@pr.oxylabs.io:7777" in url
        assert url.startswith("https://")

    def test_custom_country(self) -> None:
        provider = OxylabsProvider(username="u", password="p", country="gb")
        url = provider._build_url("icims.com")
        assert "country-gb" in url

    def test_sticky_session_includes_session_id(self) -> None:
        provider = OxylabsProvider(username="u", password="p", sticky_session=True)
        url = provider._build_url("icims.com")
        assert "sessid-" in url

    def test_sticky_session_deterministic_per_domain(self) -> None:
        """Same domain always gets the same session ID."""
        provider = OxylabsProvider(username="u", password="p", sticky_session=True)
        url1 = provider._build_url("icims.com")
        url2 = provider._build_url("icims.com")
        assert url1 == url2

    def test_sticky_session_differs_across_domains(self) -> None:
        """Different domains should (almost certainly) get different session IDs."""
        provider = OxylabsProvider(username="u", password="p", sticky_session=True)
        url_icims = provider._build_url("icims.com")
        url_workday = provider._build_url("myworkdayjobs.com")
        # Extract sessid values
        import re

        sessid_icims = re.search(r"sessid-(\d+)", url_icims)
        sessid_workday = re.search(r"sessid-(\d+)", url_workday)
        assert sessid_icims is not None
        assert sessid_workday is not None
        # Different domains should produce different session IDs
        assert sessid_icims.group(1) != sessid_workday.group(1)

    @pytest.mark.asyncio
    async def test_get_proxy_url_returns_built_url(self) -> None:
        provider = OxylabsProvider(username="u", password="p")
        url = await provider.get_proxy_url("icims.com")
        assert url is not None
        assert "pr.oxylabs.io" in url

    def test_report_success_resets_failures(self) -> None:
        provider = OxylabsProvider(username="u", password="p")
        provider.report_failure("icims.com")
        provider.report_success("icims.com")
        assert provider._failures.get("icims.com", 0) == 0

    def test_report_failure_increments(self) -> None:
        provider = OxylabsProvider(username="u", password="p")
        provider.report_failure("icims.com")
        provider.report_failure("icims.com")
        assert provider._failures["icims.com"] == 2

    def test_special_chars_in_credentials_are_escaped(self) -> None:
        """Credentials with URL-unsafe characters must be percent-encoded."""
        provider = OxylabsProvider(username="user@org", password="p@ss:w/rd")
        url = provider._build_url("icims.com")
        # @ and : must not appear unescaped in the userinfo portion
        assert "user%40org" in url
        assert "p%40ss%3Aw%2Frd" in url
        # The host portion should still be present and unescaped
        assert "@pr.oxylabs.io:7777" in url


# ---------------------------------------------------------------------------
# ProxyPool
# ---------------------------------------------------------------------------


class TestProxyPool:
    def _make_settings(
        self,
        proxy_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ):
        from compgraph.config import Settings

        kwargs: dict = {"DATABASE_PASSWORD": "test"}
        if proxy_url:
            kwargs["PROXY_URL"] = proxy_url
        if username:
            kwargs["PROXY_USERNAME"] = username
        if password:
            kwargs["PROXY_PASSWORD"] = password
        return Settings(**kwargs)

    def test_no_proxy_configured(self) -> None:
        s = self._make_settings()
        pool = ProxyPool(s)
        assert pool._provider is None

    def test_static_provider_for_non_oxylabs_url(self) -> None:
        s = self._make_settings(proxy_url="http://myproxy.example.com:8080")
        pool = ProxyPool(s)
        assert isinstance(pool._provider, StaticProxyProvider)

    def test_oxylabs_provider_for_oxylabs_url(self) -> None:
        s = self._make_settings(
            proxy_url="https://pr.oxylabs.io:7777",
            username="myuser",
            password="mypass",
        )
        pool = ProxyPool(s)
        assert isinstance(pool._provider, OxylabsProvider)

    @pytest.mark.asyncio
    async def test_get_proxy_url_none_when_no_provider(self) -> None:
        s = self._make_settings()
        pool = ProxyPool(s)
        result = await pool.get_proxy_url("icims.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_proxy_url_delegates_to_provider(self) -> None:
        s = self._make_settings(proxy_url="http://proxy.example.com:3128")
        pool = ProxyPool(s)
        url = await pool.get_proxy_url("icims.com")
        assert url == "http://proxy.example.com:3128"

    def test_report_success_no_op_when_no_provider(self) -> None:
        s = self._make_settings()
        pool = ProxyPool(s)
        pool.report_success("icims.com")  # should not raise

    def test_report_failure_no_op_when_no_provider(self) -> None:
        s = self._make_settings()
        pool = ProxyPool(s)
        pool.report_failure("icims.com")  # should not raise


# ---------------------------------------------------------------------------
# get_proxy_client_kwargs
# ---------------------------------------------------------------------------


class TestGetProxyClientKwargsUpdated:
    """Tests for the updated get_proxy_client_kwargs with domain parameter."""

    def _settings_no_proxy(self):
        from compgraph.config import Settings

        return Settings(DATABASE_PASSWORD="test")

    def _settings_static_proxy(self):
        from compgraph.config import Settings

        return Settings(DATABASE_PASSWORD="test", PROXY_URL="http://proxy.example.com:8080")

    def _settings_oxylabs(self):
        from compgraph.config import Settings

        return Settings(
            DATABASE_PASSWORD="test",
            PROXY_URL="https://pr.oxylabs.io:7777",
            PROXY_USERNAME="myuser",
            PROXY_PASSWORD="mypass",
        )

    def test_no_proxy_returns_empty_dict(self) -> None:
        result = get_proxy_client_kwargs(self._settings_no_proxy())
        assert result == {}

    def test_no_proxy_with_domain_returns_empty_dict(self) -> None:
        result = get_proxy_client_kwargs(self._settings_no_proxy(), domain="icims.com")
        assert result == {}

    def test_static_proxy_returns_proxy_key(self) -> None:
        result = get_proxy_client_kwargs(self._settings_static_proxy())
        assert "proxy" in result
        assert "proxy.example.com" in result["proxy"]

    def test_static_proxy_domain_ignored(self) -> None:
        """Domain arg has no effect for static proxies."""
        result_no_domain = get_proxy_client_kwargs(self._settings_static_proxy())
        result_with_domain = get_proxy_client_kwargs(
            self._settings_static_proxy(), domain="icims.com"
        )
        assert result_no_domain == result_with_domain

    def test_oxylabs_without_domain_returns_base_url(self) -> None:
        result = get_proxy_client_kwargs(self._settings_oxylabs())
        assert "proxy" in result
        # Without domain, falls through to static-style proxy_url_with_auth

    def test_oxylabs_with_domain_uses_domain_aware_url(self) -> None:
        result = get_proxy_client_kwargs(self._settings_oxylabs(), domain="icims.com")
        assert "proxy" in result
        assert "pr.oxylabs.io" in result["proxy"]

    def test_oxylabs_domain_url_contains_username(self) -> None:
        result = get_proxy_client_kwargs(self._settings_oxylabs(), domain="icims.com")
        assert "myuser" in result["proxy"]


# ---------------------------------------------------------------------------
# random_user_agent (regression)
# ---------------------------------------------------------------------------


class TestRandomUserAgent:
    def test_returns_string_from_pool(self) -> None:
        ua = random_user_agent()
        assert ua in _USER_AGENTS

    def test_contains_mozilla(self) -> None:
        for ua in _USER_AGENTS:
            assert "Mozilla" in ua
