"""Tests for proxy and user-agent utilities."""

from __future__ import annotations

from compgraph.scrapers.proxy import _USER_AGENTS, get_proxy_client_kwargs, random_user_agent


class TestRandomUserAgent:
    """Tests for random_user_agent()."""

    def test_returns_string(self) -> None:
        ua = random_user_agent()
        assert isinstance(ua, str)
        assert len(ua) > 0

    def test_returns_from_pool(self) -> None:
        ua = random_user_agent()
        assert ua in _USER_AGENTS

    def test_contains_mozilla(self) -> None:
        """All UAs should look like real browser strings."""
        for ua in _USER_AGENTS:
            assert "Mozilla" in ua

    def test_pool_has_variety(self) -> None:
        """Pool should have at least 3 distinct user agents."""
        assert len(_USER_AGENTS) >= 3


class TestGetProxyClientKwargs:
    """Tests for get_proxy_client_kwargs()."""

    def test_empty_dict_when_no_proxy(self, settings_override: None) -> None:
        from compgraph.config import settings

        # Default settings have no PROXY_URL
        result = get_proxy_client_kwargs(settings)
        assert result == {}

    def test_proxy_dict_with_url(self) -> None:
        """Should return proxy dict when PROXY_URL is set."""
        from compgraph.config import Settings

        s = Settings(
            DATABASE_PASSWORD="test",
            PROXY_URL="http://proxy.example.com:8080",
        )
        result = get_proxy_client_kwargs(s)
        assert result == {"proxy": "http://proxy.example.com:8080"}

    def test_proxy_url_with_credentials(self) -> None:
        """Should embed credentials in proxy URL."""
        from compgraph.config import Settings

        s = Settings(
            DATABASE_PASSWORD="test",
            PROXY_URL="http://proxy.example.com:8080",
            PROXY_USERNAME="user",
            PROXY_PASSWORD="p@ss",
        )
        result = get_proxy_client_kwargs(s)
        proxy_url = result["proxy"]
        assert "user" in proxy_url
        assert "p%40ss" in proxy_url  # URL-encoded @
        assert "proxy.example.com:8080" in proxy_url

    def test_proxy_url_username_only(self) -> None:
        """Should embed username without password."""
        from compgraph.config import Settings

        s = Settings(
            DATABASE_PASSWORD="test",
            PROXY_URL="http://proxy.example.com:8080",
            PROXY_USERNAME="user",
        )
        result = get_proxy_client_kwargs(s)
        proxy_url = result["proxy"]
        assert "user@proxy.example.com" in proxy_url


class TestProxyUrlWithAuth:
    """Tests for Settings.proxy_url_with_auth property."""

    def test_none_when_no_proxy(self) -> None:
        from compgraph.config import Settings

        s = Settings(DATABASE_PASSWORD="test")
        assert s.proxy_url_with_auth is None

    def test_raw_url_when_no_credentials(self) -> None:
        from compgraph.config import Settings

        s = Settings(
            DATABASE_PASSWORD="test",
            PROXY_URL="http://proxy.example.com:8080",
        )
        assert s.proxy_url_with_auth == "http://proxy.example.com:8080"

    def test_url_with_auth_embedded(self) -> None:
        from compgraph.config import Settings

        s = Settings(
            DATABASE_PASSWORD="test",
            PROXY_URL="http://proxy.example.com:8080",
            PROXY_USERNAME="myuser",
            PROXY_PASSWORD="mypass",
        )
        url = s.proxy_url_with_auth
        assert url is not None
        assert url.startswith("http://myuser:mypass@proxy.example.com:8080")


class TestAdaptersUseProxy:
    """Verify adapters construct httpx clients with proxy kwargs."""

    def test_icims_adapter_imports_proxy(self) -> None:
        """ICIMSAdapter.scrape should reference proxy utilities."""
        import inspect

        from compgraph.scrapers.icims import ICIMSAdapter

        source = inspect.getsource(ICIMSAdapter.scrape)
        assert "get_proxy_client_kwargs" in source
        assert "random_user_agent" in source

    def test_workday_adapter_imports_proxy(self) -> None:
        """WorkdayAdapter.scrape should reference proxy utilities."""
        import inspect

        from compgraph.scrapers.workday import WorkdayAdapter

        source = inspect.getsource(WorkdayAdapter.scrape)
        assert "get_proxy_client_kwargs" in source
        assert "random_user_agent" in source

    def test_icims_no_default_headers_classvar(self) -> None:
        """ICIMSAdapter should no longer have a DEFAULT_HEADERS ClassVar."""
        from compgraph.scrapers.icims import ICIMSAdapter

        assert not hasattr(ICIMSAdapter, "DEFAULT_HEADERS")
