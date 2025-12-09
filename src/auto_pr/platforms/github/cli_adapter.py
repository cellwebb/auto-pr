"""GitHub CLI (gh) adapter."""

import json
import logging
import subprocess
from typing import Any, cast

from auto_pr.platforms.errors import (
    MergeConflictError,
    PlatformAuthError,
    PlatformError,
    PRBlockedError,
    PRNotFoundError,
)
from auto_pr.platforms.models import (
    CheckConclusion,
    CheckInfo,
    CheckStatus,
    MergeableState,
    PRInfo,
    PRState,
    ReviewInfo,
    ReviewState,
)

logger = logging.getLogger(__name__)


class GitHubCLIAdapter:
    """Adapter for GitHub CLI (gh) operations."""

    def __init__(self) -> None:
        self._authenticated: bool | None = None

    def is_available(self) -> bool:
        """Check if gh CLI is installed and authenticated."""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
            )
            self._authenticated = result.returncode == 0
            return self._authenticated
        except FileNotFoundError:
            return False

    def _run_gh(
        self,
        args: list[str],
        check: bool = True,
        capture_json: bool = False,
    ) -> subprocess.CompletedProcess[str] | dict[str, Any] | list[Any]:
        """Run a gh CLI command.

        Args:
            args: Command arguments (without 'gh' prefix)
            check: Raise on non-zero exit code
            capture_json: Parse output as JSON

        Returns:
            CompletedProcess or parsed JSON
        """
        cmd = ["gh"] + args
        logger.debug(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check,
            )

            if capture_json and result.stdout.strip():
                parsed: dict[str, Any] | list[Any] = json.loads(result.stdout)
                return parsed
            return result

        except subprocess.CalledProcessError as e:
            stderr = e.stderr.strip() if e.stderr else ""

            if "not authenticated" in stderr.lower() or "authentication" in stderr.lower():
                raise PlatformAuthError(stderr, platform="github") from e
            if "could not find" in stderr.lower() or "not found" in stderr.lower():
                raise PRNotFoundError(0) from e
            if "merge conflict" in stderr.lower():
                raise MergeConflictError([], pr_number=None) from e

            raise PlatformError(stderr or f"gh command failed: {' '.join(args)}", platform="github") from e

    def _parse_pr_state(self, state: str, is_draft: bool = False) -> PRState:
        """Parse PR state string to enum."""
        state = state.upper()
        if state == "MERGED":
            return PRState.MERGED
        if state == "CLOSED":
            return PRState.CLOSED
        if is_draft:
            return PRState.DRAFT
        return PRState.OPEN

    def _parse_mergeable_state(self, state: str | None) -> MergeableState | None:
        """Parse mergeable state string to enum."""
        if state is None:
            return None
        state = state.upper()
        mapping = {
            "MERGEABLE": MergeableState.MERGEABLE,
            "CONFLICTING": MergeableState.CONFLICTING,
            "UNKNOWN": MergeableState.UNKNOWN,
            "BLOCKED": MergeableState.BLOCKED,
            "BEHIND": MergeableState.BEHIND,
            "UNSTABLE": MergeableState.UNSTABLE,
            "CLEAN": MergeableState.CLEAN,
            "DIRTY": MergeableState.DIRTY,
            "HAS_HOOKS": MergeableState.HAS_HOOKS,
        }
        return mapping.get(state, MergeableState.UNKNOWN)

    def _parse_check_status(self, status: str | None) -> CheckStatus:
        """Parse check status string to enum."""
        if status is None:
            return CheckStatus.QUEUED
        status = status.upper()
        if status == "COMPLETED":
            return CheckStatus.COMPLETED
        if status == "IN_PROGRESS":
            return CheckStatus.IN_PROGRESS
        return CheckStatus.QUEUED

    def _parse_check_conclusion(self, conclusion: str | None) -> CheckConclusion | None:
        """Parse check conclusion string to enum."""
        if conclusion is None:
            return None
        conclusion = conclusion.upper()
        mapping = {
            "SUCCESS": CheckConclusion.SUCCESS,
            "FAILURE": CheckConclusion.FAILURE,
            "NEUTRAL": CheckConclusion.NEUTRAL,
            "CANCELLED": CheckConclusion.CANCELLED,
            "SKIPPED": CheckConclusion.SKIPPED,
            "TIMED_OUT": CheckConclusion.TIMED_OUT,
            "ACTION_REQUIRED": CheckConclusion.ACTION_REQUIRED,
            "PENDING": CheckConclusion.PENDING,
        }
        return mapping.get(conclusion)

    def _parse_review_state(self, state: str) -> ReviewState:
        """Parse review state string to enum."""
        state = state.upper()
        mapping = {
            "APPROVED": ReviewState.APPROVED,
            "CHANGES_REQUESTED": ReviewState.CHANGES_REQUESTED,
            "COMMENTED": ReviewState.COMMENTED,
            "PENDING": ReviewState.PENDING,
            "DISMISSED": ReviewState.DISMISSED,
        }
        return mapping.get(state, ReviewState.COMMENTED)

    def _parse_pr_json(self, data: dict[str, Any]) -> PRInfo:
        """Parse gh pr view JSON output to PRInfo."""
        is_draft = data.get("isDraft", False)
        state = self._parse_pr_state(data.get("state", "OPEN"), is_draft)

        checks = []
        status_checks = data.get("statusCheckRollup", []) or []
        for check in status_checks:
            check_name = check.get("name") or check.get("context", "Unknown")
            check_status = self._parse_check_status(check.get("status"))
            check_conclusion = self._parse_check_conclusion(check.get("conclusion"))
            checks.append(
                CheckInfo(
                    name=check_name,
                    status=check_status,
                    conclusion=check_conclusion,
                    url=check.get("detailsUrl"),
                )
            )

        reviews = []
        review_data = data.get("reviews", []) or []
        for review in review_data:
            author = review.get("author", {})
            reviews.append(
                ReviewInfo(
                    user=author.get("login", "unknown"),
                    state=self._parse_review_state(review.get("state", "COMMENTED")),
                    body=review.get("body"),
                    submitted_at=review.get("submittedAt"),
                )
            )

        labels = [label.get("name", "") for label in data.get("labels", []) or []]

        mergeable_value = data.get("mergeable")
        mergeable: bool | None
        if isinstance(mergeable_value, str):
            mergeable = mergeable_value.upper() == "MERGEABLE"
        elif isinstance(mergeable_value, bool):
            mergeable = mergeable_value
        else:
            mergeable = None

        return PRInfo(
            number=data.get("number", 0),
            title=data.get("title", ""),
            body=data.get("body", "") or "",
            state=state,
            head_branch=data.get("headRefName", ""),
            base_branch=data.get("baseRefName", ""),
            url=data.get("url", ""),
            html_url=data.get("url", ""),
            mergeable=mergeable,
            mergeable_state=self._parse_mergeable_state(data.get("mergeStateStatus")),
            draft=is_draft,
            checks=checks,
            reviews=reviews,
            labels=labels,
            author=data.get("author", {}).get("login"),
            created_at=data.get("createdAt"),
            updated_at=data.get("updatedAt"),
        )

    def create_pr(
        self,
        title: str,
        body: str,
        head: str,
        base: str,
        draft: bool = False,
        reviewers: list[str] | None = None,
        labels: list[str] | None = None,
    ) -> PRInfo:
        """Create a new PR using gh CLI."""
        args = [
            "pr",
            "create",
            "--title",
            title,
            "--body",
            body,
            "--head",
            head,
            "--base",
            base,
        ]

        if draft:
            args.append("--draft")

        if reviewers:
            args.extend(["--reviewer", ",".join(reviewers)])

        if labels:
            args.extend(["--label", ",".join(labels)])

        result = self._run_gh(args)
        completed = cast(subprocess.CompletedProcess[str], result)
        pr_url = completed.stdout.strip()

        pr_number = int(pr_url.rstrip("/").split("/")[-1])
        return self.get_pr(pr_number)

    def get_pr(self, pr_number: int) -> PRInfo:
        """Get PR information using gh CLI."""
        fields = [
            "number",
            "title",
            "body",
            "state",
            "headRefName",
            "baseRefName",
            "url",
            "mergeable",
            "mergeStateStatus",
            "isDraft",
            "statusCheckRollup",
            "reviews",
            "labels",
            "author",
            "createdAt",
            "updatedAt",
        ]

        try:
            data = self._run_gh(
                ["pr", "view", str(pr_number), "--json", ",".join(fields)],
                capture_json=True,
            )
            return self._parse_pr_json(cast(dict[str, Any], data))
        except PlatformError as e:
            raise PRNotFoundError(pr_number) from e

    def update_pr(
        self,
        pr_number: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
        draft: bool | None = None,
    ) -> PRInfo:
        """Update a PR using gh CLI."""
        args = ["pr", "edit", str(pr_number)]

        if title is not None:
            args.extend(["--title", title])

        if body is not None:
            args.extend(["--body", body])

        if draft is True:
            args.append("--draft")
        elif draft is False:
            args.append("--ready")

        if args == ["pr", "edit", str(pr_number)]:
            return self.get_pr(pr_number)

        self._run_gh(args)
        return self.get_pr(pr_number)

    def close_pr(self, pr_number: int) -> None:
        """Close a PR using gh CLI."""
        self._run_gh(["pr", "close", str(pr_number)])

    def merge_pr(
        self,
        pr_number: int,
        method: str = "merge",
        commit_title: str | None = None,
        commit_message: str | None = None,
        delete_branch: bool = False,
    ) -> bool:
        """Merge a PR using gh CLI."""
        args = ["pr", "merge", str(pr_number), f"--{method}"]

        if commit_title:
            args.extend(["--subject", commit_title])

        if commit_message:
            args.extend(["--body", commit_message])

        if delete_branch:
            args.append("--delete-branch")

        try:
            self._run_gh(args)
            return True
        except MergeConflictError:
            raise
        except PlatformError as e:
            if "conflict" in str(e).lower():
                raise MergeConflictError([], pr_number=pr_number) from e
            if "blocked" in str(e).lower() or "cannot" in str(e).lower():
                raise PRBlockedError([str(e)], pr_number=pr_number) from e
            raise

    def can_merge(self, pr_number: int) -> tuple[bool, list[str]]:
        """Check if PR can be merged."""
        pr_info = self.get_pr(pr_number)
        return pr_info.can_merge, pr_info.get_blocking_reasons()

    def get_checks(self, pr_number: int) -> list[CheckInfo]:
        """Get checks for a PR."""
        pr_info = self.get_pr(pr_number)
        return pr_info.checks

    def get_reviews(self, pr_number: int) -> list[ReviewInfo]:
        """Get reviews for a PR."""
        pr_info = self.get_pr(pr_number)
        return pr_info.reviews

    def request_reviewers(self, pr_number: int, reviewers: list[str]) -> None:
        """Request reviewers for a PR."""
        self._run_gh(["pr", "edit", str(pr_number), "--add-reviewer", ",".join(reviewers)])

    def add_labels(self, pr_number: int, labels: list[str]) -> None:
        """Add labels to a PR."""
        self._run_gh(["pr", "edit", str(pr_number), "--add-label", ",".join(labels)])

    def get_default_branch(self) -> str:
        """Get repository default branch."""
        result = self._run_gh(["repo", "view", "--json", "defaultBranchRef"], capture_json=True)
        data = cast(dict[str, Any], result)
        default_ref = data.get("defaultBranchRef", {})
        if isinstance(default_ref, dict):
            return str(default_ref.get("name", "main"))
        return "main"

    def get_repo_info(self) -> dict[str, str]:
        """Get repository information."""
        result = self._run_gh(["repo", "view", "--json", "owner,name,url"], capture_json=True)
        data = cast(dict[str, Any], result)
        owner_info = data.get("owner", {})
        owner = owner_info.get("login", "") if isinstance(owner_info, dict) else ""
        return {
            "owner": str(owner),
            "repo": str(data.get("name", "")),
            "url": str(data.get("url", "")),
        }

    def list_prs(
        self,
        state: str = "open",
        head: str | None = None,
        base: str | None = None,
        limit: int = 30,
    ) -> list[PRInfo]:
        """List PRs matching criteria."""
        args = ["pr", "list", "--state", state, "--limit", str(limit)]

        if head:
            args.extend(["--head", head])

        if base:
            args.extend(["--base", base])

        fields = [
            "number",
            "title",
            "body",
            "state",
            "headRefName",
            "baseRefName",
            "url",
            "isDraft",
            "author",
            "createdAt",
        ]
        args.extend(["--json", ",".join(fields)])

        data = self._run_gh(args, capture_json=True)

        if not isinstance(data, list):
            return []

        return [self._parse_pr_json(pr) for pr in data]
