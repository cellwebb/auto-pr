"""GitHub REST API adapter."""

import logging
import os
import subprocess
from typing import Any, cast

import httpx

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


class GitHubAPIAdapter:
    """Adapter for GitHub REST API operations."""

    BASE_URL = "https://api.github.com"
    TIMEOUT = 30

    def __init__(self, token: str | None = None) -> None:
        self._token = token
        self._repo_info: dict[str, str] | None = None

    @property
    def token(self) -> str | None:
        """Get GitHub token from environment or constructor."""
        if self._token:
            return self._token
        return os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")

    def is_available(self) -> bool:
        """Check if API token is available."""
        return self.token is not None

    def _get_repo_info(self) -> dict[str, str]:
        """Get owner and repo from git remote."""
        if self._repo_info:
            return self._repo_info

        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True,
            )
            remote_url = result.stdout.strip()

            if remote_url.startswith("git@"):
                parts = remote_url.split(":")[1].replace(".git", "").split("/")
            else:
                parts = remote_url.replace(".git", "").split("/")[-2:]

            self._repo_info = {
                "owner": parts[0],
                "repo": parts[1],
                "url": f"https://github.com/{parts[0]}/{parts[1]}",
            }
            return self._repo_info

        except (subprocess.CalledProcessError, IndexError) as e:
            raise PlatformError(f"Failed to get repo info: {e}", platform="github") from e

    def _request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Make an API request.

        Args:
            method: HTTP method
            endpoint: API endpoint (without base URL)
            json_data: JSON body
            params: Query parameters

        Returns:
            Response JSON
        """
        if not self.token:
            raise PlatformAuthError("GITHUB_TOKEN not set", platform="github")

        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        logger.debug(f"API {method} {endpoint}")

        try:
            response = httpx.request(
                method,
                url,
                headers=headers,
                json=json_data,
                params=params,
                timeout=self.TIMEOUT,
            )

            if response.status_code == 401:
                raise PlatformAuthError("Invalid GitHub token", platform="github")

            if response.status_code == 404:
                raise PRNotFoundError(0)

            if response.status_code == 409:
                data = response.json() if response.content else {}
                message = data.get("message", "Conflict")
                if "merge conflict" in message.lower():
                    raise MergeConflictError([], pr_number=None)
                raise PlatformError(message, platform="github")

            if response.status_code >= 400:
                data = response.json() if response.content else {}
                message = data.get("message", f"API error {response.status_code}")
                raise PlatformError(message, platform="github")

            if response.status_code == 204:
                return {}

            result: dict[str, Any] | list[Any] = response.json()
            return result

        except httpx.TimeoutException as e:
            raise PlatformError("API request timed out", platform="github") from e
        except httpx.RequestError as e:
            raise PlatformError(f"API request failed: {e}", platform="github") from e

    def _parse_pr_state(self, state: str, merged: bool = False, draft: bool = False) -> PRState:
        """Parse PR state."""
        if merged:
            return PRState.MERGED
        if state == "closed":
            return PRState.CLOSED
        if draft:
            return PRState.DRAFT
        return PRState.OPEN

    def _parse_mergeable_state(self, mergeable_state: str | None) -> MergeableState | None:
        """Parse mergeable state."""
        if mergeable_state is None:
            return None
        mapping = {
            "clean": MergeableState.CLEAN,
            "dirty": MergeableState.DIRTY,
            "unstable": MergeableState.UNSTABLE,
            "blocked": MergeableState.BLOCKED,
            "behind": MergeableState.BEHIND,
            "unknown": MergeableState.UNKNOWN,
            "has_hooks": MergeableState.HAS_HOOKS,
        }
        return mapping.get(mergeable_state.lower(), MergeableState.UNKNOWN)

    def _parse_pr_response(self, data: dict[str, Any]) -> PRInfo:
        """Parse PR API response to PRInfo."""
        state = self._parse_pr_state(
            data.get("state", "open"),
            merged=data.get("merged", False),
            draft=data.get("draft", False),
        )

        labels = [label.get("name", "") for label in data.get("labels", [])]

        return PRInfo(
            number=data.get("number", 0),
            title=data.get("title", ""),
            body=data.get("body", "") or "",
            state=state,
            head_branch=data.get("head", {}).get("ref", ""),
            base_branch=data.get("base", {}).get("ref", ""),
            url=data.get("url", ""),
            html_url=data.get("html_url", ""),
            mergeable=data.get("mergeable"),
            mergeable_state=self._parse_mergeable_state(data.get("mergeable_state")),
            draft=data.get("draft", False),
            labels=labels,
            author=data.get("user", {}).get("login"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
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
        """Create a new PR using API."""
        repo = self._get_repo_info()

        pr_response = self._request(
            "POST",
            f"/repos/{repo['owner']}/{repo['repo']}/pulls",
            json_data={
                "title": title,
                "body": body,
                "head": head,
                "base": base,
                "draft": draft,
            },
        )
        pr_data = cast(dict[str, Any], pr_response)

        pr_number = pr_data.get("number", 0)

        if reviewers:
            self.request_reviewers(pr_number, reviewers)

        if labels:
            self.add_labels(pr_number, labels)

        return self.get_pr(pr_number)

    def get_pr(self, pr_number: int) -> PRInfo:
        """Get PR information using API."""
        repo = self._get_repo_info()

        try:
            response = self._request("GET", f"/repos/{repo['owner']}/{repo['repo']}/pulls/{pr_number}")
            data = cast(dict[str, Any], response)
            pr_info = self._parse_pr_response(data)

            pr_info.checks = self.get_checks(pr_number)
            pr_info.reviews = self.get_reviews(pr_number)

            return pr_info
        except PRNotFoundError as e:
            raise PRNotFoundError(pr_number) from e

    def update_pr(
        self,
        pr_number: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
        draft: bool | None = None,
    ) -> PRInfo:
        """Update a PR using API."""
        repo = self._get_repo_info()

        update_data: dict[str, Any] = {}
        if title is not None:
            update_data["title"] = title
        if body is not None:
            update_data["body"] = body
        if state is not None:
            update_data["state"] = state

        if update_data:
            self._request(
                "PATCH",
                f"/repos/{repo['owner']}/{repo['repo']}/pulls/{pr_number}",
                json_data=update_data,
            )

        if draft is not None:
            endpoint = "ready_for_review" if not draft else "convert_to_draft"
            try:
                self._request(
                    "PUT",
                    f"/repos/{repo['owner']}/{repo['repo']}/pulls/{pr_number}/{endpoint}",
                )
            except PlatformError:
                pass

        return self.get_pr(pr_number)

    def close_pr(self, pr_number: int) -> None:
        """Close a PR using API."""
        repo = self._get_repo_info()
        self._request(
            "PATCH",
            f"/repos/{repo['owner']}/{repo['repo']}/pulls/{pr_number}",
            json_data={"state": "closed"},
        )

    def merge_pr(
        self,
        pr_number: int,
        method: str = "merge",
        commit_title: str | None = None,
        commit_message: str | None = None,
        delete_branch: bool = False,
    ) -> bool:
        """Merge a PR using API."""
        repo = self._get_repo_info()

        merge_data: dict[str, Any] = {"merge_method": method}
        if commit_title:
            merge_data["commit_title"] = commit_title
        if commit_message:
            merge_data["commit_message"] = commit_message

        try:
            self._request(
                "PUT",
                f"/repos/{repo['owner']}/{repo['repo']}/pulls/{pr_number}/merge",
                json_data=merge_data,
            )

            if delete_branch:
                pr_info = self.get_pr(pr_number)
                try:
                    self._request(
                        "DELETE",
                        f"/repos/{repo['owner']}/{repo['repo']}/git/refs/heads/{pr_info.head_branch}",
                    )
                except PlatformError:
                    logger.warning(f"Failed to delete branch {pr_info.head_branch}")

            return True

        except MergeConflictError:
            raise
        except PlatformError as e:
            if "conflict" in str(e).lower():
                raise MergeConflictError([], pr_number=pr_number) from e
            if "blocked" in str(e).lower() or "not mergeable" in str(e).lower():
                raise PRBlockedError([str(e)], pr_number=pr_number) from e
            raise

    def can_merge(self, pr_number: int) -> tuple[bool, list[str]]:
        """Check if PR can be merged."""
        pr_info = self.get_pr(pr_number)
        return pr_info.can_merge, pr_info.get_blocking_reasons()

    def get_checks(self, pr_number: int) -> list[CheckInfo]:
        """Get checks for a PR."""
        repo = self._get_repo_info()

        pr_response = self._request("GET", f"/repos/{repo['owner']}/{repo['repo']}/pulls/{pr_number}")
        pr_data = cast(dict[str, Any], pr_response)
        head_info = pr_data.get("head", {})
        head_sha = head_info.get("sha", "") if isinstance(head_info, dict) else ""

        if not head_sha:
            return []

        checks: list[CheckInfo] = []

        try:
            check_runs_response = self._request(
                "GET",
                f"/repos/{repo['owner']}/{repo['repo']}/commits/{head_sha}/check-runs",
            )
            check_runs = cast(dict[str, Any], check_runs_response)

            for run in check_runs.get("check_runs", []):
                status_str = run.get("status", "queued")
                if status_str == "completed":
                    status = CheckStatus.COMPLETED
                elif status_str == "in_progress":
                    status = CheckStatus.IN_PROGRESS
                else:
                    status = CheckStatus.QUEUED

                conclusion = None
                if run.get("conclusion"):
                    conclusion_map = {
                        "success": CheckConclusion.SUCCESS,
                        "failure": CheckConclusion.FAILURE,
                        "neutral": CheckConclusion.NEUTRAL,
                        "cancelled": CheckConclusion.CANCELLED,
                        "skipped": CheckConclusion.SKIPPED,
                        "timed_out": CheckConclusion.TIMED_OUT,
                        "action_required": CheckConclusion.ACTION_REQUIRED,
                    }
                    conclusion = conclusion_map.get(run.get("conclusion", "").lower())

                checks.append(
                    CheckInfo(
                        name=run.get("name", "Unknown"),
                        status=status,
                        conclusion=conclusion,
                        url=run.get("html_url"),
                        started_at=run.get("started_at"),
                        completed_at=run.get("completed_at"),
                    )
                )
        except PlatformError:
            pass

        try:
            statuses = self._request(
                "GET",
                f"/repos/{repo['owner']}/{repo['repo']}/commits/{head_sha}/statuses",
            )

            for status_data in statuses if isinstance(statuses, list) else []:
                state = status_data.get("state", "pending")
                if state == "success":
                    status = CheckStatus.COMPLETED
                    conclusion = CheckConclusion.SUCCESS
                elif state == "failure" or state == "error":
                    status = CheckStatus.COMPLETED
                    conclusion = CheckConclusion.FAILURE
                else:
                    status = CheckStatus.IN_PROGRESS
                    conclusion = None

                checks.append(
                    CheckInfo(
                        name=status_data.get("context", "Unknown"),
                        status=status,
                        conclusion=conclusion,
                        url=status_data.get("target_url"),
                    )
                )
        except PlatformError:
            pass

        return checks

    def get_reviews(self, pr_number: int) -> list[ReviewInfo]:
        """Get reviews for a PR."""
        repo = self._get_repo_info()

        reviews_data = self._request(
            "GET",
            f"/repos/{repo['owner']}/{repo['repo']}/pulls/{pr_number}/reviews",
        )

        reviews: list[ReviewInfo] = []
        state_map = {
            "APPROVED": ReviewState.APPROVED,
            "CHANGES_REQUESTED": ReviewState.CHANGES_REQUESTED,
            "COMMENTED": ReviewState.COMMENTED,
            "PENDING": ReviewState.PENDING,
            "DISMISSED": ReviewState.DISMISSED,
        }

        for review in reviews_data if isinstance(reviews_data, list) else []:
            reviews.append(
                ReviewInfo(
                    user=review.get("user", {}).get("login", "unknown"),
                    state=state_map.get(review.get("state", "COMMENTED"), ReviewState.COMMENTED),
                    body=review.get("body"),
                    submitted_at=review.get("submitted_at"),
                )
            )

        return reviews

    def request_reviewers(self, pr_number: int, reviewers: list[str]) -> None:
        """Request reviewers for a PR."""
        repo = self._get_repo_info()
        self._request(
            "POST",
            f"/repos/{repo['owner']}/{repo['repo']}/pulls/{pr_number}/requested_reviewers",
            json_data={"reviewers": reviewers},
        )

    def add_labels(self, pr_number: int, labels: list[str]) -> None:
        """Add labels to a PR."""
        repo = self._get_repo_info()
        self._request(
            "POST",
            f"/repos/{repo['owner']}/{repo['repo']}/issues/{pr_number}/labels",
            json_data={"labels": labels},
        )

    def get_default_branch(self) -> str:
        """Get repository default branch."""
        repo = self._get_repo_info()
        response = self._request("GET", f"/repos/{repo['owner']}/{repo['repo']}")
        data = cast(dict[str, Any], response)
        return str(data.get("default_branch", "main"))

    def get_repo_info(self) -> dict[str, str]:
        """Get repository information."""
        return self._get_repo_info()

    def list_prs(
        self,
        state: str = "open",
        head: str | None = None,
        base: str | None = None,
        limit: int = 30,
    ) -> list[PRInfo]:
        """List PRs matching criteria."""
        repo = self._get_repo_info()

        params: dict[str, Any] = {
            "state": state,
            "per_page": min(limit, 100),
        }
        if head:
            params["head"] = f"{repo['owner']}:{head}"
        if base:
            params["base"] = base

        prs_response = self._request(
            "GET",
            f"/repos/{repo['owner']}/{repo['repo']}/pulls",
            params=params,
        )

        if isinstance(prs_response, list):
            return [self._parse_pr_response(cast(dict[str, Any], pr)) for pr in prs_response]
        return []
