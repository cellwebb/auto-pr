"""PR lifecycle state machine for tracking and managing PR states."""

from dataclasses import dataclass, field
from enum import Enum, auto

from auto_pr.platforms.models import PRInfo


class PRLifecycleState(Enum):
    """States in the PR lifecycle."""

    CREATED = auto()
    OPEN = auto()
    DRAFT = auto()
    CHECKS_RUNNING = auto()
    CHECKS_PASSED = auto()
    CHECKS_FAILED = auto()
    CONFLICT = auto()
    RESOLUTION = auto()
    BLOCKED = auto()
    REVIEW_REQUIRED = auto()
    CHANGES_REQUESTED = auto()
    READY_TO_MERGE = auto()
    MERGED = auto()
    CLOSED = auto()


@dataclass
class StateTransition:
    """Represents a valid state transition."""

    from_state: PRLifecycleState
    to_state: PRLifecycleState
    trigger: str
    description: str = ""


VALID_TRANSITIONS = [
    StateTransition(PRLifecycleState.CREATED, PRLifecycleState.OPEN, "publish", "PR published"),
    StateTransition(PRLifecycleState.CREATED, PRLifecycleState.DRAFT, "create_draft", "Created as draft"),
    StateTransition(PRLifecycleState.DRAFT, PRLifecycleState.OPEN, "ready_for_review", "Marked ready for review"),
    StateTransition(PRLifecycleState.OPEN, PRLifecycleState.DRAFT, "convert_to_draft", "Converted to draft"),
    StateTransition(PRLifecycleState.OPEN, PRLifecycleState.CHECKS_RUNNING, "checks_started", "CI checks started"),
    StateTransition(PRLifecycleState.OPEN, PRLifecycleState.REVIEW_REQUIRED, "awaiting_review", "Waiting for reviews"),
    StateTransition(
        PRLifecycleState.CHECKS_RUNNING, PRLifecycleState.CHECKS_PASSED, "checks_pass", "All checks passed"
    ),
    StateTransition(PRLifecycleState.CHECKS_RUNNING, PRLifecycleState.CHECKS_FAILED, "checks_fail", "Checks failed"),
    StateTransition(
        PRLifecycleState.CHECKS_RUNNING, PRLifecycleState.CONFLICT, "conflict_detected", "Merge conflict detected"
    ),
    StateTransition(PRLifecycleState.CHECKS_PASSED, PRLifecycleState.READY_TO_MERGE, "approved", "Reviews approved"),
    StateTransition(
        PRLifecycleState.CHECKS_PASSED, PRLifecycleState.REVIEW_REQUIRED, "awaiting_review", "Waiting for reviews"
    ),
    StateTransition(
        PRLifecycleState.CHECKS_PASSED, PRLifecycleState.CHANGES_REQUESTED, "changes_requested", "Changes requested"
    ),
    StateTransition(PRLifecycleState.CHECKS_FAILED, PRLifecycleState.BLOCKED, "blocked", "Blocked by failing checks"),
    StateTransition(PRLifecycleState.CHECKS_FAILED, PRLifecycleState.CHECKS_RUNNING, "retry", "Checks retriggered"),
    StateTransition(
        PRLifecycleState.CONFLICT, PRLifecycleState.RESOLUTION, "start_resolution", "Starting conflict resolution"
    ),
    StateTransition(
        PRLifecycleState.RESOLUTION, PRLifecycleState.CHECKS_RUNNING, "resolution_complete", "Conflicts resolved"
    ),
    StateTransition(PRLifecycleState.RESOLUTION, PRLifecycleState.CONFLICT, "resolution_failed", "Resolution failed"),
    StateTransition(PRLifecycleState.REVIEW_REQUIRED, PRLifecycleState.READY_TO_MERGE, "approved", "Reviews approved"),
    StateTransition(
        PRLifecycleState.REVIEW_REQUIRED, PRLifecycleState.CHANGES_REQUESTED, "changes_requested", "Changes requested"
    ),
    StateTransition(
        PRLifecycleState.CHANGES_REQUESTED, PRLifecycleState.REVIEW_REQUIRED, "addressed", "Changes addressed"
    ),
    StateTransition(
        PRLifecycleState.CHANGES_REQUESTED, PRLifecycleState.CHECKS_RUNNING, "pushed", "New commits pushed"
    ),
    StateTransition(PRLifecycleState.BLOCKED, PRLifecycleState.CHECKS_RUNNING, "unblocked", "Block removed"),
    StateTransition(PRLifecycleState.READY_TO_MERGE, PRLifecycleState.MERGED, "merge", "PR merged"),
    StateTransition(PRLifecycleState.READY_TO_MERGE, PRLifecycleState.CONFLICT, "conflict", "New conflict"),
    StateTransition(PRLifecycleState.READY_TO_MERGE, PRLifecycleState.BLOCKED, "blocked", "Merge blocked"),
    StateTransition(PRLifecycleState.OPEN, PRLifecycleState.CLOSED, "close", "PR closed"),
    StateTransition(PRLifecycleState.DRAFT, PRLifecycleState.CLOSED, "close", "PR closed"),
    StateTransition(PRLifecycleState.BLOCKED, PRLifecycleState.CLOSED, "close", "PR closed"),
]


@dataclass
class PRStateMachine:
    """State machine for managing PR lifecycle."""

    current_state: PRLifecycleState = PRLifecycleState.CREATED
    history: list[tuple[PRLifecycleState, str]] = field(default_factory=list)
    pr_number: int | None = None

    def can_transition(self, trigger: str) -> bool:
        """Check if a transition is valid from current state."""
        return any(t.from_state == self.current_state and t.trigger == trigger for t in VALID_TRANSITIONS)

    def get_valid_triggers(self) -> list[str]:
        """Get list of valid triggers from current state."""
        return [t.trigger for t in VALID_TRANSITIONS if t.from_state == self.current_state]

    def transition(self, trigger: str) -> PRLifecycleState:
        """Execute a state transition.

        Args:
            trigger: The trigger event

        Returns:
            The new state

        Raises:
            ValueError: If transition is invalid
        """
        for t in VALID_TRANSITIONS:
            if t.from_state == self.current_state and t.trigger == trigger:
                self.history.append((self.current_state, trigger))
                self.current_state = t.to_state
                return self.current_state

        valid = self.get_valid_triggers()
        raise ValueError(f"Invalid transition: '{trigger}' from {self.current_state.name}. Valid triggers: {valid}")

    def set_state(self, state: PRLifecycleState) -> None:
        """Directly set state (for initialization from PR data)."""
        if state != self.current_state:
            self.history.append((self.current_state, "direct_set"))
            self.current_state = state

    @classmethod
    def from_pr_info(cls, pr_info: PRInfo) -> "PRStateMachine":
        """Create state machine initialized from PR info.

        Args:
            pr_info: PR information from platform

        Returns:
            Initialized state machine
        """
        machine = cls(pr_number=pr_info.number)
        state = cls.determine_state(pr_info)
        machine.current_state = state
        return machine

    @staticmethod
    def determine_state(pr_info: PRInfo) -> PRLifecycleState:
        """Determine the lifecycle state from PR info.

        Args:
            pr_info: PR information from platform

        Returns:
            Determined lifecycle state
        """
        if pr_info.is_merged:
            return PRLifecycleState.MERGED

        if not pr_info.is_open:
            return PRLifecycleState.CLOSED

        if pr_info.is_draft:
            return PRLifecycleState.DRAFT

        if pr_info.has_conflicts:
            return PRLifecycleState.CONFLICT

        if pr_info.checks_pending:
            return PRLifecycleState.CHECKS_RUNNING

        if pr_info.checks_failed:
            return PRLifecycleState.CHECKS_FAILED

        changes_requested = [r for r in pr_info.reviews if r.requests_changes]
        if changes_requested:
            return PRLifecycleState.CHANGES_REQUESTED

        if not pr_info.is_approved and pr_info.reviews:
            return PRLifecycleState.REVIEW_REQUIRED

        blocking_reasons = pr_info.get_blocking_reasons()
        if blocking_reasons:
            return PRLifecycleState.BLOCKED

        if pr_info.can_merge:
            return PRLifecycleState.READY_TO_MERGE

        if pr_info.checks_passed:
            return PRLifecycleState.CHECKS_PASSED

        return PRLifecycleState.OPEN

    def get_state_description(self) -> str:
        """Get human-readable description of current state."""
        descriptions = {
            PRLifecycleState.CREATED: "PR created, not yet published",
            PRLifecycleState.OPEN: "PR is open",
            PRLifecycleState.DRAFT: "PR is a draft",
            PRLifecycleState.CHECKS_RUNNING: "CI/CD checks are running",
            PRLifecycleState.CHECKS_PASSED: "All checks passed",
            PRLifecycleState.CHECKS_FAILED: "Some checks failed",
            PRLifecycleState.CONFLICT: "Merge conflicts detected",
            PRLifecycleState.RESOLUTION: "Resolving conflicts",
            PRLifecycleState.BLOCKED: "PR is blocked from merging",
            PRLifecycleState.REVIEW_REQUIRED: "Waiting for reviews",
            PRLifecycleState.CHANGES_REQUESTED: "Changes have been requested",
            PRLifecycleState.READY_TO_MERGE: "Ready to merge",
            PRLifecycleState.MERGED: "PR has been merged",
            PRLifecycleState.CLOSED: "PR has been closed",
        }
        return descriptions.get(self.current_state, "Unknown state")

    def can_merge(self) -> bool:
        """Check if PR can be merged in current state."""
        return self.current_state == PRLifecycleState.READY_TO_MERGE

    def needs_attention(self) -> bool:
        """Check if PR needs user attention."""
        attention_states = {
            PRLifecycleState.CONFLICT,
            PRLifecycleState.CHECKS_FAILED,
            PRLifecycleState.BLOCKED,
            PRLifecycleState.CHANGES_REQUESTED,
        }
        return self.current_state in attention_states

    def is_terminal(self) -> bool:
        """Check if PR is in a terminal state."""
        return self.current_state in {PRLifecycleState.MERGED, PRLifecycleState.CLOSED}
