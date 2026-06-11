"""
Camada de dados - Banco de dados SQLite estruturado
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "dados" / "jarvis.db"


class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        """Inicializa o banco de dados com as tabelas necessárias."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Tabela de tarefas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    done BOOLEAN DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de lembretes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    remind_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de eventos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time TEXT,
                    description TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de despesas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL NOT NULL,
                    description TEXT,
                    category TEXT,
                    date TEXT DEFAULT CURRENT_TIMESTAMP,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de histórico de comandos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS command_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT,
                    result TEXT,
                    success BOOLEAN DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de sessões
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mode TEXT NOT NULL,
                    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    ended_at TEXT,
                    commands_count INTEGER DEFAULT 0
                )
            """)

            # Tabela de preferências do usuário
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    @staticmethod
    def get_connection() -> sqlite3.Connection:
        """Retorna uma conexão com o banco de dados."""
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def transaction(self):
        """Context manager para transações."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ============ TASKS ============

    def add_task(self, text: str) -> int:
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tasks (text) VALUES (?)", (text,))
            return cursor.lastrowid

    def get_tasks(self, include_done: bool = True) -> List[Dict]:
        with self.transaction() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM tasks"
            if not include_done:
                query += " WHERE done = 0"
            query += " ORDER BY created_at DESC"
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def mark_task_done(self, task_id: int) -> bool:
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET done = 1, updated_at = ? WHERE id = ?",
                         (datetime.now().isoformat(), task_id))
            return cursor.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return cursor.rowcount > 0

    # ============ REMINDERS ============

    def add_reminder(self, text: str, remind_at: Optional[str] = None) -> int:
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO reminders (text, remind_at) VALUES (?, ?)",
                         (text, remind_at))
            return cursor.lastrowid

    def get_reminders(self, pending_only: bool = True) -> List[Dict]:
        with self.transaction() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM reminders"
            if pending_only:
                query += " WHERE remind_at IS NULL OR remind_at > ?"
                cursor.execute(query, (datetime.now().isoformat(),))
            else:
                cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    # ============ EVENTS ============

    def add_event(self, title: str, date: str, time: Optional[str] = None,
                  description: Optional[str] = None) -> int:
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO events (title, date, time, description) VALUES (?, ?, ?, ?)",
                (title, date, time, description)
            )
            return cursor.lastrowid

    def get_events(self, date: Optional[str] = None) -> List[Dict]:
        with self.transaction() as conn:
            cursor = conn.cursor()
            if date:
                cursor.execute("SELECT * FROM events WHERE date = ? ORDER BY time", (date,))
            else:
                cursor.execute("SELECT * FROM events ORDER BY date, time")
            return [dict(row) for row in cursor.fetchall()]

    # ============ EXPENSES ============

    def add_expense(self, amount: float, description: str = "",
                    category: Optional[str] = None) -> int:
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO expenses (amount, description, category) VALUES (?, ?, ?)",
                (amount, description, category)
            )
            return cursor.lastrowid

    def get_expenses(self, start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> List[Dict]:
        with self.transaction() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM expenses WHERE 1=1"
            params = []
            if start_date:
                query += " AND date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND date <= ?"
                params.append(end_date)
            query += " ORDER BY date DESC"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_expense_summary(self) -> Dict:
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    COUNT(*) as total_count,
                    SUM(amount) as total_amount,
                    AVG(amount) as avg_amount
                FROM expenses
            """)
            row = cursor.fetchone()
            return dict(row) if row else {}

    # ============ COMMAND HISTORY ============

    def log_command(self, command: str, action: str, target: str = "",
                    result: str = "", success: bool = True) -> int:
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO command_history (command, action, target, result, success)
                VALUES (?, ?, ?, ?, ?)
            """, (command, action, target, result, success))
            return cursor.lastrowid

    def get_command_history(self, limit: int = 100) -> List[Dict]:
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM command_history
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_commands(self, action: Optional[str] = None, limit: int = 50) -> List[str]:
        with self.transaction() as conn:
            cursor = conn.cursor()
            if action:
                cursor.execute("""
                    SELECT command FROM command_history
                    WHERE action = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (action, limit))
            else:
                cursor.execute("""
                    SELECT command FROM command_history
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
            return [row['command'] for row in cursor.fetchall()]

    # ============ USER PREFERENCES ============

    def set_preference(self, key: str, value: Any) -> None:
        with self.transaction() as conn:
            cursor = conn.cursor()
            value_json = json.dumps(value) if not isinstance(value, str) else value
            cursor.execute("""
                INSERT OR REPLACE INTO user_preferences (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value_json, datetime.now().isoformat()))

    def get_preference(self, key: str, default: Any = None) -> Any:
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row['value'])
                except json.JSONDecodeError:
                    return row['value']
            return default

    # ============ SESSIONS ============

    def start_session(self, mode: str) -> int:
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (mode, started_at)
                VALUES (?, ?)
            """, (mode, datetime.now().isoformat()))
            return cursor.lastrowid

    def end_session(self, session_id: int, commands_count: int) -> None:
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions
                SET ended_at = ?, commands_count = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), commands_count, session_id))


# Instância global
db = Database()