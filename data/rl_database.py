"""
Jarvis Data Layer - Camada de Persistência SQL
Módulo de banco de dados para armazenamento persistente de dados de aprendizado
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from config.settings import DATA_DIR


class JarvisDatabase:
    """Banco de dados SQLite para persistência de dados do Jarvis."""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or (DATA_DIR / "jarvis_learning.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        """Obtém conexão com o banco de dados."""
        return sqlite3.connect(str(self.db_path))

    @contextmanager
    def _cursor(self):
        """Context manager para cursor do banco."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_db(self):
        """Inicializa o banco de dados com as tabelas necessárias."""
        with self._cursor() as cursor:
            # Tabela de feedbacks individuais (histórico completo)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedbacks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    reward_type TEXT NOT NULL,
                    reward_value REAL NOT NULL,
                    context TEXT DEFAULT '',
                    command TEXT DEFAULT '',
                    result TEXT DEFAULT '',
                    success BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Índice para consultas por ação e contexto
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedbacks_action
                ON feedbacks(action)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedbacks_context
                ON feedbacks(context)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedbacks_created
                ON feedbacks(created_at)
            """)

            # Tabela de estatísticas agregadas por ação
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS action_stats (
                    action TEXT PRIMARY KEY,
                    total_score REAL DEFAULT 0.0,
                    use_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    avg_score REAL DEFAULT 0.0,
                    success_rate REAL DEFAULT 0.0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de scores por contexto
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS context_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context TEXT NOT NULL,
                    action TEXT NOT NULL,
                    score REAL DEFAULT 0.0,
                    use_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(context, action)
                )
            """)

            # Índice para contexto
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_context_scores_context
                ON context_scores(context)
            """)

            # Tabela de métricas de aprendizado (tendências, etc)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learning_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT UNIQUE NOT NULL,
                    metric_value REAL DEFAULT 0.0,
                    json_data TEXT DEFAULT '{}',
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de preferências do usuário (padroes aprendidos)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    preference_key TEXT UNIQUE NOT NULL,
                    preference_value TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    sample_count INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de histórico de comandos (para análise)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS command_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command_text TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT DEFAULT '',
                    result TEXT DEFAULT '',
                    success BOOLEAN DEFAULT 1,
                    execution_time_ms INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_command_history_action
                ON command_history(action)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_command_history_created
                ON command_history(created_at)
            """)

    def log_feedback(self, action: str, reward_type: str, reward_value: float,
                    context: str = "", command: str = "", result: str = "",
                    success: bool = True) -> int:
        """Registra um feedback individual e retorna o ID."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO feedbacks
                (action, reward_type, reward_value, context, command, result, success)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (action, reward_type, reward_value, context, command, result, success))
            return cursor.lastrowid

    def update_action_stats(self, action: str, reward_value: float, success: bool):
        """Atualiza estatísticas agregadas de uma ação."""
        with self._cursor() as cursor:
            # Verificar se existe
            cursor.execute("SELECT use_count, success_count FROM action_stats WHERE action = ?", (action,))
            row = cursor.fetchone()

            if row:
                use_count, success_count = row
                new_use_count = use_count + 1
                new_success_count = success_count + (1 if success else 0)
                new_total_score = (cursor.execute(
                    "SELECT total_score FROM action_stats WHERE action = ?", (action,)
                ).fetchone()[0] or 0) + reward_value
                new_avg = new_total_score / new_use_count
                new_success_rate = new_success_count / new_use_count

                cursor.execute("""
                    UPDATE action_stats SET
                        total_score = ?,
                        use_count = ?,
                        success_count = ?,
                        failure_count = failure_count + ?,
                        avg_score = ?,
                        success_rate = ?,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE action = ?
                """, (new_total_score, new_use_count, new_success_count,
                      0 if success else 1, new_avg, new_success_rate, action))
            else:
                cursor.execute("""
                    INSERT INTO action_stats
                    (action, total_score, use_count, success_count, failure_count, avg_score, success_rate)
                    VALUES (?, ?, 1, ?, 0, ?, ?)
                """, (action, reward_value, 1 if success else 0, reward_value,
                      1.0 if success else 0.0))

    def update_context_score(self, context: str, action: str, reward_value: float, success: bool):
        """Atualiza score de uma ação em um contexto específico."""
        if not context:
            return

        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO context_scores (context, action, score, use_count, success_count)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(context, action) DO UPDATE SET
                    score = score + excluded.score,
                    use_count = use_count + 1,
                    success_count = success_count + excluded.success_count,
                    last_updated = CURRENT_TIMESTAMP
            """, (context, action, reward_value, 1 if success else 0))

    def get_action_stats(self, action: str) -> dict:
        """Retorna estatísticas de uma ação específica."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT total_score, use_count, success_count, failure_count,
                       avg_score, success_rate, last_updated
                FROM action_stats WHERE action = ?
            """, (action,))
            row = cursor.fetchone()

            if not row:
                return None

            return {
                "action": action,
                "total_score": row[0],
                "use_count": row[1],
                "success_count": row[2],
                "failure_count": row[3],
                "avg_score": row[4],
                "success_rate": row[5],
                "last_updated": row[6]
            }

    def get_context_actions(self, context: str, limit: int = 10) -> list:
        """Retorna as melhores ações para um contexto específico."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT action, score, use_count, success_count,
                       CAST(success_count AS REAL) / CAST(use_count AS REAL) as success_rate
                FROM context_scores
                WHERE context = ?
                ORDER BY score DESC
                LIMIT ?
            """, (context, limit))

            return [
                {"action": row[0], "score": row[1], "use_count": row[2],
                 "success_count": row[3], "success_rate": row[4]}
                for row in cursor.fetchall()
            ]

    def get_top_actions(self, limit: int = 10) -> list:
        """Retorna as ações com melhor score global."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT action, total_score, use_count, avg_score, success_rate
                FROM action_stats
                ORDER BY total_score DESC
                LIMIT ?
            """, (limit,))

            return [
                {"action": row[0], "score": row[1], "times": row[2],
                 "avg_score": row[3], "success_rate": row[4]}
                for row in cursor.fetchall()
            ]

    def get_learning_summary(self) -> dict:
        """Retorna resumo do aprendizado do sistema."""
        with self._cursor() as cursor:
            # Total de feedbacks
            cursor.execute("SELECT COUNT(*) FROM feedbacks")
            total_feedbacks = cursor.fetchone()[0]

            # Total de ações únicas
            cursor.execute("SELECT COUNT(*) FROM action_stats")
            unique_actions = cursor.fetchone()[0]

            # Ações com score positivo
            cursor.execute("SELECT COUNT(*) FROM action_stats WHERE total_score > 0")
            positive_actions = cursor.fetchone()[0]

            # Ações com score negativo
            cursor.execute("SELECT COUNT(*) FROM action_stats WHERE total_score < 0")
            negative_actions = cursor.fetchone()[0]

            # Último feedback
            cursor.execute("SELECT created_at FROM feedbacks ORDER BY id DESC LIMIT 1")
            last_feedback = cursor.fetchone()[0]

            return {
                "total_feedbacks": total_feedbacks,
                "unique_actions": unique_actions,
                "positive_actions": positive_actions,
                "negative_actions": negative_actions,
                "last_feedback": last_feedback
            }

    def get_recent_trends(self, days: int = 7) -> dict:
        """Retorna tendências recentes de aprendizado."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT action,
                       COUNT(*) as count,
                       SUM(reward_value) as total_reward,
                       AVG(reward_value) as avg_reward
                FROM feedbacks
                WHERE created_at >= datetime('now', '-' || ? || ' days')
                GROUP BY action
                ORDER BY count DESC
            """, (days,))

            return [
                {"action": row[0], "count": row[1],
                 "total_reward": row[2], "avg_reward": row[3]}
                for row in cursor.fetchall()
            ]

    def get_action_history(self, action: str, limit: int = 50) -> list:
        """Retorna histórico de feedbacks de uma ação."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT reward_type, reward_value, context, command, success, created_at
                FROM feedbacks
                WHERE action = ?
                ORDER BY id DESC
                LIMIT ?
            """, (action, limit))

            return [
                {"reward_type": row[0], "reward_value": row[1],
                 "context": row[2], "command": row[3],
                 "success": row[4], "created_at": row[5]}
                for row in cursor.fetchall()
            ]

    def set_preference(self, key: str, value: str, confidence: float = 0.5, sample_count: int = 1):
        """Define uma preferência do usuário."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO user_preferences (preference_key, preference_value, confidence, sample_count)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(preference_key) DO UPDATE SET
                    preference_value = excluded.preference_value,
                    confidence = (confidence * sample_count + excluded.confidence * excluded.sample_count)
                                 / (sample_count + excluded.sample_count),
                    sample_count = sample_count + excluded.sample_count,
                    last_updated = CURRENT_TIMESTAMP
            """, (key, value, confidence, sample_count))

    def get_preference(self, key: str) -> dict:
        """Retorna uma preferência do usuário."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT preference_key, preference_value, confidence, sample_count, last_updated
                FROM user_preferences WHERE preference_key = ?
            """, (key,))
            row = cursor.fetchone()

            if not row:
                return None

            return {
                "key": row[0],
                "value": row[1],
                "confidence": row[2],
                "sample_count": row[3],
                "last_updated": row[4]
            }

    def log_command(self, command_text: str, action: str, target: str = "",
                    result: str = "", success: bool = True, execution_time_ms: int = 0):
        """Registra um comando no histórico."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO command_history
                (command_text, action, target, result, success, execution_time_ms)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (command_text, action, target, result, success, execution_time_ms))

    def get_best_action_for_context(self, context: str, available_actions: list = None) -> dict:
        """Retorna a melhor ação para um contexto considerando ações disponíveis."""
        with self._cursor() as cursor:
            if available_actions:
                placeholders = ','.join(['?' for _ in available_actions])
                cursor.execute(f"""
                    SELECT cs.action, cs.score, cs.use_count,
                           CAST(cs.success_count AS REAL) / CAST(cs.use_count AS REAL) as success_rate,
                           COALESCE(a.total_score, 0) as global_score
                    FROM context_scores cs
                    LEFT JOIN action_stats a ON cs.action = a.action
                    WHERE cs.context = ? AND cs.action IN ({placeholders})
                    ORDER BY cs.score DESC
                    LIMIT 5
                """, (context, *available_actions))
            else:
                cursor.execute("""
                    SELECT cs.action, cs.score, cs.use_count,
                           CAST(cs.success_count AS REAL) / CAST(cs.use_count AS REAL) as success_rate,
                           COALESCE(a.total_score, 0) as global_score
                    FROM context_scores cs
                    LEFT JOIN action_stats a ON cs.action = a.action
                    WHERE cs.context = ?
                    ORDER BY cs.score DESC
                    LIMIT 5
                """, (context,))

            rows = cursor.fetchall()
            if not rows:
                # Fallback para global
                return self._get_best_global_action(available_actions)

            # Calcular score combinado
            best = rows[0]
            combined_score = (best[1] * 1.5) + (best[4] * 0.5)  # Contexto tem peso maior

            return {
                "action": best[0],
                "score": round(best[1], 2),
                "use_count": best[2],
                "success_rate": round(best[3], 2) if best[3] else 0,
                "source": "context",
                "combined_score": round(combined_score, 2)
            }

    def _get_best_global_action(self, available_actions: list = None) -> dict:
        """Retorna a melhor ação globalmente (fallback)."""
        with self._cursor() as cursor:
            if available_actions:
                placeholders = ','.join(['?' for _ in available_actions])
                cursor.execute(f"""
                    SELECT action, total_score, use_count, success_rate
                    FROM action_stats
                    WHERE action IN ({placeholders})
                    ORDER BY total_score DESC
                    LIMIT 1
                """, (*available_actions,))
            else:
                cursor.execute("""
                    SELECT action, total_score, use_count, success_rate
                    FROM action_stats
                    ORDER BY total_score DESC
                    LIMIT 1
                """)

            row = cursor.fetchone()
            if not row:
                return {"action": None, "score": 0, "source": "no_data"}

            return {
                "action": row[0],
                "score": round(row[1], 2),
                "use_count": row[2],
                "success_rate": round(row[3], 2) if row[3] else 0,
                "source": "global"
            }

    def get_all_contexts(self) -> list:
        """Retorna todos os contextos únicos."""
        with self._cursor() as cursor:
            cursor.execute("SELECT DISTINCT context FROM context_scores ORDER BY context")
            return [row[0] for row in cursor.fetchall() if row[0]]

    def decay_scores(self, factor: float = 0.95):
        """Aplica decaimento aos scores (reduz pesos antigos)."""
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE action_stats
                SET total_score = total_score * ?,
                    avg_score = avg_score * ?,
                    last_updated = CURRENT_TIMESTAMP
            """, (factor, factor))

            cursor.execute("""
                UPDATE context_scores
                SET score = score * ?,
                    last_updated = CURRENT_TIMESTAMP
            """, (factor,))

    def clear_old_feedbacks(self, keep_last: int = 10000):
        """Remove feedbacks antigos mantendo apenas os últimos N."""
        with self._cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM feedbacks")
            total = cursor.fetchone()[0]

            if total > keep_last:
                cursor.execute("""
                    DELETE FROM feedbacks
                    WHERE id <= (SELECT id FROM feedbacks ORDER BY id DESC LIMIT 1 OFFSET ?)
                """, (keep_last,))

            return {"deleted": total - keep_last if total > keep_last else 0, "remaining": min(total, keep_last)}


# Instância global
_db = None


def get_database() -> JarvisDatabase:
    """Retorna a instância global do banco de dados."""
    global _db
    if _db is None:
        _db = JarvisDatabase()
    return _db