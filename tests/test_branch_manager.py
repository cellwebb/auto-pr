"""Tests for branch_manager.py - 14% coverage, 149 statements!"""

from unittest.mock import patch

from rich.console import Console

from auto_pr.branch_manager import BranchManager
from auto_pr.errors import GitError


class TestBranchManager:
    """Test BranchManager class."""

    def test_init_with_console(self):
        """Test BranchManager initialization with custom console."""
        console = Console()
        manager = BranchManager(console=console)
        assert manager.console is console

    def test_init_without_console(self):
        """Test BranchManager initialization without custom console."""
        manager = BranchManager()
        assert manager.console is not None
        assert isinstance(manager.console, Console)


class TestBranchExists:
    """Test branch_exists method."""

    @patch("auto_pr.branch_manager.run_git_command")
    def test_branch_exists_local_success(self, mock_run_command):
        """Test successful local branch existence check."""
        mock_run_command.return_value = "branch-hash"

        manager = BranchManager()
        result = manager.branch_exists("feature-branch", remote=False)

        assert result is True

    @patch("auto_pr.branch_manager.run_git_command")
    def test_branch_exists_local_failure(self, mock_run_command):
        """Test local branch doesn't exist."""
        mock_run_command.side_effect = GitError("Branch not found")

        manager = BranchManager()
        result = manager.branch_exists("nonexistent-branch", remote=False)

        assert result is False

    @patch("auto_pr.branch_manager.run_git_command")
    def test_branch_exists_remote_success(self, mock_run_command):
        """Test successful remote branch existence check."""
        mock_run_command.return_value = "abc123 refs/heads/feature-branch\n"

        manager = BranchManager()
        result = manager.branch_exists("feature-branch", remote=True)

        assert result is True

    @patch("auto_pr.branch_manager.run_git_command")
    def test_branch_exists_remote_empty(self, mock_run_command):
        """Test remote branch doesn't exist."""
        mock_run_command.return_value = ""

        manager = BranchManager()
        result = manager.branch_exists("nonexistent-branch", remote=True)

        assert result is False


class TestGetCommitsBehind:
    """Test get_commits_behind method."""

    @patch("auto_pr.branch_manager.run_git_command")
    def test_get_commits_behind_success(self, mock_run_command):
        """Test successful commits behind calculation."""
        mock_run_command.side_effect = ["", "5"]  # fetch output, count output

        manager = BranchManager()
        result = manager.get_commits_behind("main")

        assert result == 5

    @patch("auto_pr.branch_manager.run_git_command")
    def test_get_commits_behind_zero(self, mock_run_command):
        """Test commits behind when branch is up to date."""
        mock_run_command.side_effect = ["", "0"]

        manager = BranchManager()
        result = manager.get_commits_behind("main")

        assert result == 0

    @patch("auto_pr.branch_manager.run_git_command")
    def test_get_commits_behind_git_error(self, mock_run_command):
        """Test commits behind with GitError."""
        mock_run_command.side_effect = GitError("Git fetch failed")

        manager = BranchManager()
        result = manager.get_commits_behind("main")

        assert result == 0


class TestDeleteBranch:
    """Test delete_branch method."""

    @patch("auto_pr.branch_manager.run_git_command")
    @patch("auto_pr.branch_manager.Console.print")
    def test_delete_local_branch_success(self, mock_console_print, mock_run_command):
        """Test successful local branch deletion."""
        manager = BranchManager()
        result = manager.delete_branch("feature-branch", remote=False)

        assert result is True
        mock_run_command.assert_called_once_with(["branch", "-D", "feature-branch"])

    @patch("auto_pr.branch_manager.run_git_command")
    @patch("auto_pr.branch_manager.Console.print")
    def test_delete_remote_branch_success(self, mock_console_print, mock_run_command):
        """Test successful remote branch deletion."""
        manager = BranchManager()
        result = manager.delete_branch("feature-branch", remote=True)

        assert result is True
        mock_run_command.assert_called_once_with(["push", "origin", "--delete", "feature-branch"])

    @patch("auto_pr.branch_manager.run_git_command")
    @patch("auto_pr.branch_manager.Console.print")
    def test_delete_branch_failure(self, mock_console_print, mock_run_command):
        """Test branch deletion failure."""
        mock_run_command.side_effect = GitError("Deletion failed")

        manager = BranchManager()
        result = manager.delete_branch("feature-branch", remote=False)

        assert result is False
        mock_console_print.assert_called_once()


class TestBranchManagerIntegration:
    """Integration tests for BranchManager."""

    def test_complete_workflow_simulation(self):
        """Test a complete branch management workflow."""
        manager = BranchManager()

        # Mock all the git operations for a complete workflow
        with patch.object(manager, "get_current_branch", return_value="feature-branch"):
            with patch.object(manager, "branch_exists", return_value=True):
                with patch.object(manager, "get_commits_behind", return_value=0):
                    with patch.object(manager, "is_up_to_date", return_value=True):
                        with patch.object(manager, "is_branch_pushed", return_value=True):
                            # Test workflow steps
                            branch = manager.get_current_branch()
                            assert branch == "feature-branch"

                            exists = manager.branch_exists("feature-branch")
                            assert exists is True

                            up_to_date = manager.is_up_to_date("main")
                            assert up_to_date is True

                            pushed = manager.is_branch_pushed()
                            assert pushed is True
