"""OpenRouter API provider for auto-pr."""

from auto_pr.providers.base import OpenAICompatibleProvider, ProviderConfig


class OpenRouterProvider(OpenAICompatibleProvider):
    config = ProviderConfig(
        name="OpenRouter",
        api_key_env="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1",
    )

    def _get_api_url(self, model: str | None = None) -> str:
        """Get OpenRouter API URL with /chat/completions endpoint."""
        return f"{self.config.base_url}/chat/completions"

    def _build_headers(self) -> dict[str, str]:
        """Build headers with OpenRouter-style authorization and HTTP-Referer."""
        headers = super()._build_headers()
        headers["HTTP-Referer"] = "https://github.com/cellwebb/auto-pr"
        return headers
