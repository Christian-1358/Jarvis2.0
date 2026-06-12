"""
Tests for JarvisDB core database.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.core_database import JarvisDB

class TestJarvisDBInit:
    """Tests for database initialization."""

    def test_create_database(self, temp_db_path):
        """Test database creation."""
        db = JarvisDB(db_path=temp_db_path)
        assert temp_db_path.exists()

    def test_schema_version(self, temp_db_path):
        """Test schema version is set."""
        db = JarvisDB(db_path=temp_db_path)
        with db._conn() as conn:
            cursor = conn.execute("SELECT value FROM db_meta WHERE key = 'schema_version'")
            row = cursor.fetchone()
            assert row is not None
            assert int(row[0]) >= 1


class TestWorkspaceTasks:
    """Tests for workspace task operations."""

    def test_create_workspace(self, temp_db_path):
        """Test workspace creation."""
        db = JarvisDB(db_path=temp_db_path)
        ws_id = db.create_workspace("Test Workspace", "Descrição teste")
        assert ws_id > 0

    def test_create_task(self, temp_db_path):
        """Test task creation."""
        db = JarvisDB(db_path=temp_db_path)
        ws_id = db.create_workspace("Test", "desc")
        task_id = db.add_workspace_task(ws_id, "Tarefa teste", priority=1)
        assert task_id > 0

    def test_update_task_status(self, temp_db_path):
        """Test task status update with SQL injection fix."""
        db = JarvisDB(db_path=temp_db_path)
        ws_id = db.create_workspace("Test", "desc")
        task_id = db.add_workspace_task(ws_id, "Tarefa teste")

        # Test completed status
        result = db.update_task_status(task_id, "completed")
        assert result is True

        tasks = db.get_workspace_tasks(ws_id)
        completed_task = next((t for t in tasks if t["id"] == task_id), None)
        assert completed_task is not None
        assert completed_task["status"] == "completed"
        assert completed_task["completed_at"] is not None

        # Test pending status
        result = db.update_task_status(task_id, "pending")
        assert result is True

        tasks = db.get_workspace_tasks(ws_id)
        updated_task = next((t for t in tasks if t["id"] == task_id), None)
        assert updated_task["status"] == "pending"
        assert updated_task["completed_at"] is None

    def test_update_task_status_sql_injection_safe(self, temp_db_path):
        """Test that status update is safe from SQL injection."""
        db = JarvisDB(db_path=temp_db_path)
        ws_id = db.create_workspace("Test", "desc")
        task_id = db.add_workspace_task(ws_id, "Tarefa")

        # Attempt SQL injection via status
        malicious_status = "completed'; DROP TABLE workspace_tasks; --"
        try:
            db.update_task_status(task_id, malicious_status)
        except Exception:
            pass  # Should either reject or handle safely

        # Verify table still exists
        with db._conn() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM workspace_tasks")
            count = cursor.fetchone()[0]
            assert count >= 0  # Table should still exist


class TestConversationLogging:
    """Tests for conversation logging."""

    def test_log_conversation(self, temp_db_path):
        """Test conversation logging."""
        db = JarvisDB(db_path=temp_db_path)
        db.log_conversation(
            session_id="test-123",
            role="user",
            message="test command",
            action="open_app",
            target="chrome",
            result="opened"
        )

    def test_get_conversation_history(self, temp_db_path):
        """Test retrieving conversation history."""
        db = JarvisDB(db_path=temp_db_path)
        session_id = "test-456"

        db.log_conversation(session_id, "user", "msg1", "action1", "t1", "r1")
        db.log_conversation(session_id, "assistant", "msg2", "action2", "t2", "r2")

        history = db.get_conversation_history(session_id, limit=10)
        assert len(history) == 2


class TestUsageStats:
    """Tests for usage statistics."""

    def test_increment_usage(self, temp_db_path):
        """Test usage increment."""
        db = JarvisDB(db_path=temp_db_path)
        db.increment_usage("open_app", success=True)
        db.increment_usage("open_app", success=True)
        db.increment_usage("open_app", success=False)

        summary = db.get_usage_summary(days=7)
        assert "total_actions" in summary or "actions" in summary


class TestRLStats:
    """Tests for reinforcement learning stats."""

    def test_update_rl_stats(self, temp_db_path):
        """Test RL stats update."""
        db = JarvisDB(db_path=temp_db_path)
        db.update_rl_stats("open_app", reward_value=1.0, success=True)
        db.update_rl_stats("open_app", reward_value=-0.5, success=False)

    def test_update_rl_context(self, temp_db_path):
        """Test RL context update."""
        db = JarvisDB(db_path=temp_db_path)
        db.update_rl_context("browser", "open_app", reward_value=1.0, success=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])