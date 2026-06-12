"""
Pytest fixtures for Jarvis tests.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime


@pytest.fixture
def temp_dir():
    """Temporary directory for test files."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)


@pytest.fixture
def temp_db_path(temp_dir):
    """Temporary database path."""
    return temp_dir / "test_jarvis.db"


@pytest.fixture
def sample_workspace_data():
    """Sample workspace data for testing."""
    return {
        "name": f"test_workspace_{datetime.now().timestamp()}",
        "description": "Workspace de teste",
        "tasks": [
            {"title": "Tarefa 1", "status": "pending", "priority": 1},
            {"title": "Tarefa 2", "status": "completed", "priority": 2},
        ]
    }


@pytest.fixture
def sample_conversation():
    """Sample conversation for testing."""
    return {
        "session_id": "test-session-123",
        "messages": [
            {"role": "user", "message": " abre o chrome", "action": "open_app", "target": "chrome"},
            {"role": "assistant", "message": "Chrome aberto", "action": "open_app", "target": "chrome", "result": "sucesso"},
        ]
    }