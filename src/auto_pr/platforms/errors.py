"""Platform-specific error types."""

from auto_pr.errors import AutoPRError


class PlatformError(AutoPRError):
    """Base error for Git platform operations (GitHub, GitLab, etc.)."""

    exit_code = 7

    def __init__(
        self,
        message: str,
        platform: str | None = None,
        details: str | None = None,
        suggestion: str | None = None,
    ):
        super().__init__(message, details=details, suggestion=suggestion)
        self.platform = platform


class PlatformAuthError(PlatformError):
    """Authentication error with Git platform."""

    exit_code = 7

    def __init__(self, message: str, platform: str | None = None):
        suggestion = None
        if platform == "github":
            suggestion = "Run 'gh auth login' or set GITHUB_TOKEN environment variable"
        elif platform == "gitlab":
            suggestion = "Run 'glab auth login' or set GITLAB_TOKEN environment variable"
        super().__init__(message, platform=platform, suggestion=suggestion)


class PlatformNotFoundError(PlatformError):
    """Platform CLI or API not available."""

    exit_code = 7

    def __init__(self, platform: str):
        message = f"{platform} CLI not found and no API token configured"
        suggestion = f"Install {platform} CLI or configure API token"
        super().__init__(message, platform=platform, suggestion=suggestion)


class MergeConflictError(PlatformError):
    """Merge conflicts detected in PR."""

    exit_code = 8

    def __init__(self, conflicts: list[str], pr_number: int | None = None):
        self.conflicts = conflicts
        self.pr_number = pr_number
        message = f"Merge conflicts detected in {len(conflicts)} file(s)"
        details = "\n".join(f"  - {f}" for f in conflicts[:10])
        if len(conflicts) > 10:
            details += f"\n  ... and {len(conflicts) - 10} more"
        suggestion = "Resolve conflicts by rebasing or merging the base branch"
        super().__init__(message, details=details, suggestion=suggestion)


class ChecksFailedError(PlatformError):
    """CI/CD checks failed on PR."""

    exit_code = 9

    def __init__(self, failed_checks: list[str], pr_number: int | None = None):
        self.failed_checks = failed_checks
        self.pr_number = pr_number
        message = f"{len(failed_checks)} CI/CD check(s) failed"
        details = "\n".join(f"  - {c}" for c in failed_checks[:10])
        suggestion = "Fix the failing checks or use --ignore-checks to proceed"
        super().__init__(message, details=details, suggestion=suggestion)


class ChecksPendingError(PlatformError):
    """CI/CD checks still running."""

    exit_code = 9

    def __init__(self, pending_checks: list[str], pr_number: int | None = None):
        self.pending_checks = pending_checks
        self.pr_number = pr_number
        message = f"{len(pending_checks)} CI/CD check(s) still running"
        details = "\n".join(f"  - {c}" for c in pending_checks[:10])
        suggestion = "Wait for checks to complete or use --no-wait-checks"
        super().__init__(message, details=details, suggestion=suggestion)


class PRBlockedError(PlatformError):
    """PR is blocked from merging."""

    exit_code = 10

    def __init__(self, reasons: list[str], pr_number: int | None = None):
        self.reasons = reasons
        self.pr_number = pr_number
        message = "PR cannot be merged"
        details = "\n".join(f"  - {r}" for r in reasons)
        super().__init__(message, details=details)


class ReviewRequiredError(PlatformError):
    """Required reviews not satisfied."""

    exit_code = 10

    def __init__(
        self,
        required: int,
        approved: int,
        pr_number: int | None = None,
        changes_requested_by: list[str] | None = None,
    ):
        self.required = required
        self.approved = approved
        self.pr_number = pr_number
        self.changes_requested_by = changes_requested_by or []

        if changes_requested_by:
            message = f"Changes requested by: {', '.join(changes_requested_by)}"
        else:
            message = f"Need {required - approved} more approval(s) ({approved}/{required})"
        super().__init__(message)


class PRNotFoundError(PlatformError):
    """PR not found."""

    exit_code = 7

    def __init__(self, pr_number: int):
        message = f"Pull request #{pr_number} not found"
        super().__init__(message)


class BranchNotFoundError(PlatformError):
    """Branch not found."""

    exit_code = 7

    def __init__(self, branch: str):
        message = f"Branch '{branch}' not found"
        super().__init__(message)
