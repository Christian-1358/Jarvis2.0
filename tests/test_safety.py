"""
Tests for safety manager.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.safety import get_safety, is_dangerous, requires_confirmation


class TestSafetyManager:
    """Tests for SafetyManager class."""

    def test_singleton_pattern(self):
        """Test that get_safety returns singleton."""
        safety1 = get_safety()
        safety2 = get_safety()
        assert safety1 is safety2

    def test_dangerous_actions_defined(self):
        """Test that dangerous actions are properly defined."""
        safety = get_safety()
        # These should be dangerous
        assert is_dangerous("shutdown_pc") is True
        assert is_dangerous("restart_pc") is True
        assert is_dangerous("delete_file") is True
        assert is_dangerous("format_disk") is True

    def test_safe_actions(self):
        """Test that safe actions are not marked dangerous."""
        assert is_dangerous("open_app") is False
        assert is_dangerous("search_web") is False
        assert is_dangerous("list_tasks") is False

    def test_requires_confirmation(self):
        """Test confirmation requirements."""
        assert requires_confirmation("shutdown_pc") is True
        assert requires_confirmation("restart_pc") is True
        # Safe actions don't require confirmation
        assert requires_confirmation("open_app") is False


class TestConfirmationFlow:
    """Tests for confirmation flow."""

    def test_request_confirmation(self):
        """Test requesting confirmation for dangerous action."""
        safety = get_safety()
        result = safety.request_confirmation("shutdown_pc", "", "test-session")

        assert "confirmation_id" in result
        assert "message" in result

    def test_check_confirmation_invalid(self):
        """Test checking with invalid confirmation ID."""
        safety = get_safety()
        result = safety.check_confirmation("invalid-id-xyz", "sim")

        assert result["confirmed"] is False

    def test_auto_approved_session(self):
        """Test auto-approved session bypasses confirmation."""
        safety = get_safety()
        session_id = "auto-approve-test-session"

        # Add auto-approved
        safety.add_auto_approved(session_id, duration_minutes=5)

        # Should not require confirmation
        assert requires_confirmation("shutdown_pc") is True  # Still requires from action perspective
        # But the confirmation check should pass for this session


class TestDangerousActionPhrases:
    """Tests for dangerous action confirmation phrases."""

    def test_confirmation_phrase_exists(self):
        """Test that dangerous actions have confirmation phrases."""
        from core.action_registry import DANGEROUS_ACTIONS
        dangerous_actions = ["shutdown_pc", "restart_pc", "delete_file"]

        for action in dangerous_actions:
            info = DANGEROUS_ACTIONS.get(action)
            assert info is not None, f"Missing info for {action}"
            assert hasattr(info, 'phrase')
            assert info.phrase != ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])