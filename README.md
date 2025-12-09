<!-- markdownlint-disable MD013 -->
<!-- markdownlint-disable MD033 MD036 -->

<div align="center">

# 🚀 Auto-PR

[![PyPI version](https://img.shields.io/pypi/v/auto-pr.svg)](https://pypi.org/project/auto-pr/)
[![Python](https://img.shields.io/badge/python-3.10--3.14-blue.svg)](https://www.python.org/downloads/)
[![Build Status](https://github.com/cellwebb/auto-pr/actions/workflows/ci.yml/badge.svg)](https://github.com/cellwebb/auto-pr/actions)
[![codecov](https://codecov.io/gh/cellwebb/auto-pr/branch/main/graph/badge.svg)](https://app.codecov.io/gh/cellwebb/auto-pr)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](https://mypy-lang.org/)
[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](docs/en/CONTRIBUTING.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**LLM-powered pull requests and merge commits that understand your code!**

**Automate your PRs!** Generate comprehensive pull request descriptions and merge commit messages with AI-powered analysis of your code changes!

---

## What You Get

Intelligent, contextual PR descriptions that explain the **why** behind your changes:

_Auto-PR generating a contextual PR description_

---

</div>

<!-- markdownlint-enable MD033 MD036 -->

## Quick Start

### Use auto-pr without installing

```bash
uvx auto-pr init   # Configure your provider, model, and language
uvx auto-pr create-pr  # Generate and create a PR with AI
uvx auto-pr merge-pr   # Generate an AI-powered merge commit
```

That's it! Review the generated description and confirm with `y`.

### Install and use auto-pr

```bash
pip install auto-pr
auto-pr init   # Set up your AI provider and preferences
auto-pr create-pr  # Create a new PR with AI-generated description
```

## Features

### 🤖 Multi-Provider AI Support

- **25+ AI providers**: OpenAI, Anthropic, Gemini, Groq, Ollama, and many more
- **Model flexibility**: Use any model from any supported provider
- **Consistent interface**: Same experience across all AI providers

### 📝 Smart PR Generation

- **Contextual descriptions**: AI analyzes your code changes to generate meaningful PR descriptions
- **Structured format**: Automatic generation of Summary, Changes, Testing, and Impact sections
- **Multiple languages**: Support for 13+ languages for global teams
- **Customizable templates**: Add your own PR description templates

### 🔀 Merge Commit Intelligence

- **Semantic merge messages**: Generate conventional commit-style merge messages
- **Context-aware**: Include relevant context from the PR description
- **Integration ready**: Perfect for automated merge workflows

### 🛡️ Full PR Lifecycle Management

- **Merge conflict handling**: Automatic detection with guided or auto-resolution (rebase/merge)
- **CI/CD check monitoring**: Wait for checks, handle failures, retry flaky tests
- **Branch management**: Sync with base branch, force-push safely after rebase
- **Review workflows**: Track approval status, request reviewers automatically

### 🛠 Developer Experience

- **Interactive mode**: Ask questions to gather more context for better PR descriptions
- **Dry run mode**: Preview PR content before creating
- **Draft PRs**: Create draft PRs for review before publishing
- **Configuration management**: Easy setup and configuration

## Usage

### Creating Pull Requests

```bash
# Create a PR for current branch (compare to main)
auto-pr create-pr

# Compare to a different base branch
auto-pr create-pr --base develop

# Create as draft
auto-pr create-pr --draft

# Generate title only (no full description)
auto-pr create-pr --title-only

# Interactive mode with questions
auto-pr create-pr --interactive

# Preview without creating
auto-pr create-pr --dry-run

# Generate in Spanish
auto-pr create-pr --language Spanish

# Use specific model
auto-pr create-pr --model openai:gpt-4

# Verbose mode with detailed testing instructions
auto-pr create-pr --verbose

# Request reviewers and add labels
auto-pr create-pr --reviewer user1 --reviewer user2 --label bug

# Wait for CI checks after creating
auto-pr create-pr --wait-checks

# Sync branch with base before creating PR
auto-pr create-pr --sync
```

### Merging Pull Requests

```bash
# Generate merge commit and merge PR #123
auto-pr merge-pr --pr-number 123

# Use squash merge
auto-pr merge-pr --pr-number 123 --merge-method squash

# Generate only merge commit message (don't merge)
auto-pr merge-pr --pr-number 123 --message-only

# Use specific model for merge message
auto-pr merge-pr --pr-number 123 --model anthropic:claude-3-sonnet

# Skip waiting for CI checks
auto-pr merge-pr --pr-number 123 --no-wait-checks

# Auto-resolve conflicts via rebase
auto-pr merge-pr --pr-number 123 --auto-resolve

# Delete branch after merging
auto-pr merge-pr --pr-number 123 --delete-branch
```

### Creating Branches from Changes

```bash
# Generate branch name from staged changes
auto-pr create-branch

# Include unstaged changes in analysis
auto-pr create-branch --include-unstaged

# Provide context for better branch names
auto-pr create-branch --hint "user authentication feature"

# Create branch without checking it out
auto-pr create-branch --no-checkout
```

### Checking PR Status

```bash
# Show current branch status and any open PR
auto-pr status

# Show specific PR status with checks and reviews
auto-pr status --pr-number 123
```

### Updating Existing PRs

```bash
# Update PR #456 description
auto-pr update-pr --pr-number 456

# Generate in French
auto-pr update-pr --pr-number 456 --language French
```

## Configuration

Run `auto-pr init` to interactively configure:

- AI provider and model selection
- API key setup
- Language preferences
- Default options

Or use environment variables:

```bash
export AUTO_PR_MODEL="openai:gpt-4"
export AUTO_PR_LANGUAGE="English"
export OPENAI_API_KEY="your-api-key"
```

## Supported AI Providers

Auto-PR supports 25+ AI providers:

- **OpenAI**: GPT-3.5/4, GPT-4o, etc.
- **Anthropic**: Claude 3 family
- **Google**: Gemini models
- **Groq**: Mixtral, Llama, etc.
- **Ollama**: Local models
- **And 20+ more**: Azure OpenAI, Together AI, Replicate, etc.

## Examples

### Generated PR Description

```markdown
## Summary

This PR adds OAuth2 authentication support for external providers, allowing users to authenticate using Google and GitHub accounts instead of local credentials.

## Changes

- **Added**: OAuth2 authentication flow with Google and GitHub providers
- **Added**: New auth service with token management and validation
- **Modified**: User login UI to include social login options
- **Added**: Database migrations for OAuth token storage

## Testing

1. **Prerequisites**: Create OAuth apps in Google and GitHub developer consoles
2. **Manual Testing**:
   - Navigate to login page
   - Click "Sign in with Google" and "Sign in with GitHub"
   - Verify OAuth redirect and token storage
   - Test user session creation
3. **Automated Tests**: Run `pytest tests/test_auth_oauth.py`
4. **Edge Cases**: Test revoked tokens, network failures, duplicate accounts
5. **Rollback Plan**: Disable OAuth in config, revert to local auth only

## Impact

- **Performance**: Minimal impact, OAuth calls are async
- **Compatibility**: Backward compatible with existing local auth
- **Breaking Changes**: None
- **Security**: Improves security by leveraging OAuth2 providers
```

### Generated Merge Commit Message

```text
feat(auth): add OAuth2 integration for external providers

Implement OAuth2 authentication flow with Google and GitHub providers.
Users can now authenticate using external accounts instead of
local credentials.

Closes #123
```

## Development

```bash
# Clone and setup
git clone https://github.com/cellwebb/auto-pr.git
cd auto-pr
uv venv && uv pip install -e ".[dev]"

# Run tests
uv run pytest

# Lint and format
uv run ruff check .
uv run ruff format .

# Build
uv run build
```

## Contributing

Contributions are welcome! Please see our [Contributing Guide](docs/en/CONTRIBUTING.md) for details.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

Auto-PR is based on the excellent work from the [Auto-PR](https://github.com/cellwebb/gac) project, adapted specifically for pull request and merge commit workflows.

---

Made with ❤️ for developers who hate writing PR descriptions
