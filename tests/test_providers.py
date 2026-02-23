"""Tests for LLM provider wrapper."""

from unittest.mock import AsyncMock, MagicMock, patch

from eval.providers import LLMResponse, call_llm


class TestLLMResponse:
    def test_response_dataclass(self):
        """LLMResponse should store all fields."""
        resp = LLMResponse(
            content='{"role_archetype": "field_rep"}',
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            latency_ms=500,
        )
        assert resp.content == '{"role_archetype": "field_rep"}'
        assert resp.cost_usd == 0.001


class TestCallLLM:
    async def test_call_returns_response(self):
        """call_llm should return LLMResponse with content and metrics."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"role_archetype": "field_rep"}'
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response._hidden_params = {"response_cost": 0.001}

        with patch("eval.providers.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            result = await call_llm(
                model="haiku-4.5",
                system_prompt="You are a test.",
                user_message="Hello.",
                max_tokens=1024,
            )
            assert result.content == '{"role_archetype": "field_rep"}'
            assert result.input_tokens == 100
            assert result.output_tokens == 50
            mock_llm.assert_called_once()

    async def test_call_passes_model_string(self):
        """call_llm should resolve model alias to LiteLLM model string."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "{}"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response._hidden_params = {"response_cost": 0.0}

        with patch("eval.providers.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            await call_llm("haiku-4.5", "sys", "user", 1024)
            call_kwargs = mock_llm.call_args
            assert call_kwargs.kwargs["model"] == "openrouter/anthropic/claude-haiku-4-5"
