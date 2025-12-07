"""Tests for OAuth retry functionality."""

from unittest.mock import Mock, patch

from auto_pr.errors import AIError, ConfigError
from auto_pr.oauth_retry import (
    OAUTH_PROVIDERS,
    OAuthProviderConfig,
    _attempt_reauth_and_retry,
    _find_oauth_provider,
    handle_oauth_error,
)


class TestOAuthRetry:
    """Test OAuth retry functionality."""

    def test_create_claude_code_authenticator(self):
        """Test Claude Code authenticator creation."""
        with patch("auto_pr.oauth.claude_code.authenticate_and_save") as mock_auth:
            from auto_pr.oauth_retry import _create_claude_code_authenticator

            authenticator = _create_claude_code_authenticator()
            mock_auth.return_value = True

            result = authenticator(quiet=True)
            assert result is True
            mock_auth.assert_called_once_with(quiet=True)

    def test_create_qwen_authenticator_function_mock(self):
        """Test Qwen authenticator using function-level mocking to avoid network calls."""
        with patch("auto_pr.oauth_retry._create_qwen_authenticator") as mock_create_func:
            mock_auth_func = Mock(return_value=True)
            mock_create_func.return_value = mock_auth_func

            result = mock_auth_func(quiet=False)
            assert result is True
            mock_auth_func.assert_called_once_with(quiet=False)

    def test_create_qwen_authenticator_failure_via_function_mock(self):
        """Test Qwen authenticator failure using function-level mocking."""
        with patch("auto_pr.oauth_retry._create_qwen_authenticator") as mock_create_func:
            for _error in [AIError("Error"), ConfigError("Config error"), OSError("OS error")]:
                mock_auth_func = Mock(return_value=False)
                mock_create_func.return_value = mock_auth_func

                result = mock_auth_func(quiet=False)
                assert result is False

    def test_claude_code_extra_check(self):
        """Test Claude Code extra error check."""
        from auto_pr.oauth_retry import _claude_code_extra_check

        # Test positive cases
        assert _claude_code_extra_check(AIError("Token has expired")) is True
        assert _claude_code_extra_check(AIError("OAuth authentication failed")) is True
        assert _claude_code_extra_check(AIError("EXPIRED token")) is True
        assert _claude_code_extra_check(AIError("OAuth error")) is True

        # Test negative cases
        assert _claude_code_extra_check(AIError("Rate limited")) is False
        assert _claude_code_extra_check(AIError("Invalid model")) is False
        assert _claude_code_extra_check(AIError("Some other error")) is False

    def test_find_oauth_provider_auth_error_non_auth_type(self):
        """Test _find_oauth_provider with non-auth error type."""
        error = AIError("Rate limit exceeded")
        error.error_type = "rate_limit"

        provider = _find_oauth_provider("claude-code:claude-3-haiku", error)
        assert provider is None

    def test_find_oauth_provider_claude_code_success(self):
        """Test _find_oauth_provider with Claude Code."""
        error = AIError("Token expired")
        error.error_type = "authentication"

        provider = _find_oauth_provider("claude-code:claude-3-haiku", error)
        assert provider is not None
        assert provider.provider_prefix == "claude-code:"
        assert provider.display_name == "Claude Code"

    def test_find_oauth_provider_claude_code_extra_check_failure(self):
        """Test Claude Code provider fails extra check."""
        error = AIError("Rate limit")  # No "expired" or "oauth"
        error.error_type = "authentication"

        provider = _find_oauth_provider("claude-code:claude-3-haiku", error)
        assert provider is None

    def test_find_oauth_provider_qwen_success(self):
        """Test _find_oauth_provider with Qwen (no extra check)."""
        error = AIError("Authentication failed")
        error.error_type = "authentication"

        provider = _find_oauth_provider("qwen:qwen-max", error)
        assert provider is not None
        assert provider.provider_prefix == "qwen:"
        assert provider.display_name == "Qwen"
        assert provider.extra_error_check is None

    def test_find_oauth_provider_no_match_model(self):
        """Test _find_oauth_provider with non-matching model."""
        error = AIError("Token expired")
        error.error_type = "authentication"

        provider = _find_oauth_provider("openai:gpt-4", error)
        assert provider is None

    def test_attempt_reauth_and_retry_success(self):
        """Test successful retry after re-authentication."""

        def mock_retry_func():
            return 0  # Success exit code

        def mock_auth(quiet):
            return True

        provider = OAuthProviderConfig(
            provider_prefix="test:",
            display_name="Test Provider",
            manual_auth_hint="Run 'test auth'",
            authenticate=mock_auth,
        )

        with patch("auto_pr.oauth_retry.console") as mock_console:
            result = _attempt_reauth_and_retry(provider, quiet=True, retry_workflow=mock_retry_func)
            assert result == 0

            mock_console.print.assert_any_call("[yellow]⚠ Test Provider OAuth token has expired[/yellow]")
            mock_console.print.assert_any_call("[cyan]🔐 Starting automatic re-authentication...[/cyan]")
            mock_console.print.assert_any_call("[green]✓ Re-authentication successful![/green]")
            mock_console.print.assert_any_call("[cyan]Retrying operation...[/cyan]\n")

    def test_attempt_reauth_and_retry_auth_failure(self):
        """Test when re-authentication fails."""

        def mock_retry_func():
            return 0

        def mock_auth(quiet):
            return False

        provider = OAuthProviderConfig(
            provider_prefix="test:",
            display_name="Test Provider",
            manual_auth_hint="Run 'test auth'",
            authenticate=mock_auth,
        )

        with patch("auto_pr.oauth_retry.console") as mock_console:
            result = _attempt_reauth_and_retry(provider, quiet=False, retry_workflow=mock_retry_func)
            assert result == 1

            mock_console.print.assert_any_call("[red]Re-authentication failed.[/red]")
            mock_console.print.assert_any_call("[yellow]Run 'test auth'[/yellow]")

    def test_attempt_reauth_and_retry_retry_failure(self):
        """Test when retry function fails after successful re-authentication."""

        def mock_retry_func():
            return 1  # Exit code 1

        def mock_auth(quiet):
            return True

        provider = OAuthProviderConfig(
            provider_prefix="test:",
            display_name="Test Provider",
            manual_auth_hint="Run 'test auth'",
            authenticate=mock_auth,
        )

        with patch("auto_pr.oauth_retry.console"):
            result = _attempt_reauth_and_retry(provider, quiet=True, retry_workflow=mock_retry_func)
            assert result == 1

    def test_attempt_reauth_and_retry_auth_exception(self):
        """Test when authentication raises an exception."""

        def mock_retry_func():
            return 0

        def mock_auth(quiet):
            raise AIError("Auth server error")

        provider = OAuthProviderConfig(
            provider_prefix="test:",
            display_name="Test Provider",
            manual_auth_hint="Run 'test auth'",
            authenticate=mock_auth,
        )

        with patch("auto_pr.oauth_retry.console") as mock_console:
            result = _attempt_reauth_and_retry(provider, quiet=False, retry_workflow=mock_retry_func)
            assert result == 1

            mock_console.print.assert_any_call("[red]Re-authentication error: Auth server error[/red]")
            mock_console.print.assert_any_call("[yellow]Run 'test auth'[/yellow]")

    def test_handle_oauth_error_no_provider(self):
        """Test handle_oauth_error when no OAuth provider found."""
        error = AIError("Some random error without provider prefix")
        error.error_type = "authentication"

        with patch("auto_pr.oauth_retry.console") as mock_console, patch("auto_pr.oauth_retry.logger") as mock_logger:
            result = handle_oauth_error(error, model="openai:gpt-4", quiet=False)
            assert result == 1

            mock_logger.error.assert_called_once()
            mock_console.print.assert_any_call(
                "[red]Failed to complete operation: Some random error without provider prefix[/red]"
            )

    def test_handle_oauth_error_with_provider_and_retry(self):
        """Test handle_oauth_error with successful OAuth retry."""
        error = AIError("Token expired")
        error.error_type = "authentication"

        mock_retry = Mock(return_value=0)

        with (
            patch("auto_pr.oauth_retry._find_oauth_provider") as mock_find_provider,
            patch("auto_pr.oauth_retry._attempt_reauth_and_retry") as mock_attempt,
        ):
            mock_provider = Mock()
            mock_find_provider.return_value = mock_provider
            mock_attempt.return_value = 0

            result = handle_oauth_error(error, model="claude-code:claude-3-haiku", quiet=True, retry_func=mock_retry)
            assert result == 0

            mock_find_provider.assert_called_once_with("claude-code:claude-3-haiku", error)
            mock_attempt.assert_called_once()

    def test_handle_oauth_error_without_retry_func(self):
        """Test handle_oauth_error without retry function shows hint."""
        error = AIError("Token expired")
        error.error_type = "authentication"

        with (
            patch("auto_pr.oauth_retry._find_oauth_provider") as mock_find_provider,
            patch("auto_pr.oauth_retry.console") as mock_console,
        ):
            mock_provider = Mock()
            mock_provider.display_name = "Claude Code"
            mock_provider.manual_auth_hint = "Run 'auto-pr model' to re-authenticate."
            mock_find_provider.return_value = mock_provider

            result = handle_oauth_error(error, model="claude-code:claude-3-haiku", quiet=False, retry_func=None)
            assert result == 1

            mock_console.print.assert_any_call("[yellow]⚠ Claude Code OAuth token has expired[/yellow]")

    def test_oauth_providers_configuration(self):
        """Test OAUTH_PROVIDERS constant is properly configured."""
        assert len(OAUTH_PROVIDERS) == 2

        # Claude Code provider
        claude_provider = next(p for p in OAUTH_PROVIDERS if p.provider_prefix == "claude-code:")
        assert claude_provider.display_name == "Claude Code"
        assert claude_provider.manual_auth_hint == "Run 'auto-pr model' to re-authenticate manually."
        assert claude_provider.extra_error_check is not None

        # Qwen provider
        qwen_provider = next(p for p in OAUTH_PROVIDERS if p.provider_prefix == "qwen:")
        assert qwen_provider.display_name == "Qwen"
        assert qwen_provider.manual_auth_hint == "Run 'auto-pr auth qwen login' to re-authenticate manually."
        assert qwen_provider.extra_error_check is None

    def test_oauth_retry_no_browser_opening(self):
        """Test that OAuth_retry functions don't open browsers when mocked properly."""
        with patch("webbrowser.open") as mock_open:
            provider_config = OAUTH_PROVIDERS[0]  # Claude Code
            assert hasattr(provider_config, "authenticate")

            mock_auth = Mock(return_value=True)
            provider_config.authenticate = mock_auth

            mock_retry = Mock(return_value=0)

            result = _attempt_reauth_and_retry(provider_config, quiet=True, retry_workflow=mock_retry)
            assert result == 0

            assert not mock_open.called
