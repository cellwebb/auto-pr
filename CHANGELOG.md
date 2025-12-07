# Changelog

All notable changes to [Auto-PR](https://github.com/cellwebb/auto-pr) will be documented in this file.

## [1.0.0] - 2025-01-XX

### Added

- Initial release of Auto-PR, a tool for generating pull requests and merge commits using AI
- Multi-provider AI support with 25+ providers (OpenAI, Anthropic, Gemini, Groq, Ollama, etc.)
- PR creation workflow with `auto-pr create-pr` command
- PR merge workflow with `auto-pr merge-pr` command
- PR update workflow with `auto-pr update-pr` command
- Support for multiple languages (13+ languages)
- Interactive mode for gathering context
- Draft PR support
- Dry run mode for preview
- Structured PR description templates
- Conventional commit-style merge messages

### Changed

- Forked from Auto-PR project and adapted for PR/merge workflows
- Renamed package from `gac` to `auto-pr`
- CLI command changed from `gac` to `auto-pr`
- Updated templates for PR descriptions and merge commits
- Simplified configuration focused on PR workflows

### Removed

- Commit-specific features (staging, grouping commits)
- Internationalized documentation (keeping English only for now)
- Commit-specific test files and examples

---

## Legacy Changes (from Auto-PR project)

Previous versions were maintained as Git Auto Commit (gac). See the [gac changelog](https://github.com/cellwebb/gac/blob/main/CHANGELOG.md) for historical changes.
