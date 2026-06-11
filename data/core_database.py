"""
Jarvis Core Database - Schema SQL Unificado
Camada de persistência centralizada para todo o sistema Jarvis
Escalável, seguro e preparado para futuras migrações
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from config.settings import DATA_DIR


class JarvisDB:
    """Banco de dados centralizado do Jarvis."""

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or (DATA_DIR / "jarvis_core.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self):
        """Context manager para conexão."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self):
        """Inicializa o schema completo do banco."""
        with self._conn() as conn:
            cursor = conn.cursor()

            # Tabela de controle de versão
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS db_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Verificar se schema já foi aplicado
            cursor.execute("SELECT value FROM db_meta WHERE key = 'schema_version'")
            row = cursor.fetchone()
            if row and int(row[0]) >= self.SCHEMA_VERSION:
                return

            # ============================================
            # TABELAS DE CONVERSAS E CONTEXTO
            # ============================================

            # Histórico de conversas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                    message TEXT NOT NULL,
                    action TEXT,
                    target TEXT,
                    result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conv_created ON conversations(created_at)")

            # Contexto da conversa atual
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(session_id, key)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ctx_session ON conversation_context(session_id)")

            # ============================================
            # TABELAS DE MEMÓRIA PERSISTENTE
            # ============================================

            # Memória de longo prazo
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    context TEXT,
                    confidence REAL DEFAULT 1.0,
                    use_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, key)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mem_category ON user_memory(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mem_key ON user_memory(key)")

            # Histórico de entidades aprendidas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    properties TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ent_type ON entities(entity_type)")

            # ============================================
            # TABELAS DE FEEDBACK E AVALIAÇÃO
            # ============================================

            # Feedback de ações
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS action_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    command TEXT,
                    reward_type TEXT NOT NULL CHECK(reward_type IN ('correct', 'incorrect', 'neutral')),
                    reward_value REAL NOT NULL,
                    context TEXT,
                    result TEXT,
                    success BOOLEAN,
                    rating INTEGER CHECK(rating IN (-1, 0, 1)),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fb_action ON action_feedback(action)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fb_context ON action_feedback(context)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fb_created ON action_feedback(created_at)")

            # ============================================
            # TABELAS DE AÇÕES E EXECUÇÃO
            # ============================================

            # Ações executadas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS action_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    target TEXT,
                    parameters TEXT,
                    result TEXT,
                    success BOOLEAN,
                    execution_time_ms INTEGER,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_act_action ON action_history(action)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_act_created ON action_history(created_at)")

            # ============================================
            # TABELAS DE APRENDIZADO POR REFORÇO
            # ============================================

            # Estatísticas de ações (agregado)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rl_action_stats (
                    action TEXT PRIMARY KEY,
                    total_score REAL DEFAULT 0.0,
                    use_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    avg_score REAL DEFAULT 0.0,
                    success_rate REAL DEFAULT 0.0,
                    last_reward_at TIMESTAMP,
                    last_used_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Scores por contexto
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rl_context_scores (
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
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rl_ctx ON rl_context_scores(context)")

            # Histórico de recompensas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rl_rewards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    reward_type TEXT NOT NULL,
                    reward_value REAL NOT NULL,
                    context TEXT,
                    session_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rl_reward_action ON rl_rewards(action)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rl_reward_created ON rl_rewards(created_at)")

            # ============================================
            # TABELAS DE ESTATÍSTICAS E MÉTRICAS
            # ============================================

            # Estatísticas agregadas por período
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    hour INTEGER,
                    action TEXT NOT NULL,
                    count INTEGER DEFAULT 0,
                    avg_execution_time_ms REAL,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    UNIQUE(date, hour, action)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_date ON usage_stats(date)")

            # ============================================
            # TABELAS DE ANALISE DE PROJETOS
            # ============================================

            # Projetos analisados
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analyzed_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT NOT NULL,
                    project_path TEXT NOT NULL,
                    total_files INTEGER DEFAULT 0,
                    files_analyzed INTEGER DEFAULT 0,
                    score REAL DEFAULT 100.0,
                    confidence REAL DEFAULT 0.5,
                    issues_count INTEGER DEFAULT 0,
                    analysis_duration_ms INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_proj_name ON analyzed_projects(project_name)")

            # Erros encontrados em analises
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_issues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    issue_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    file TEXT NOT NULL,
                    line INTEGER DEFAULT 0,
                    message TEXT,
                    suggestion TEXT,
                    code_snippet TEXT,
                    rule_id TEXT,
                    confidence REAL DEFAULT 0.8,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES analyzed_projects(id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_issue_type ON analysis_issues(issue_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_issue_severity ON analysis_issues(severity)")

            # Sugestoes e feedback
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issue_id INTEGER,
                    project_id INTEGER NOT NULL,
                    issue_type TEXT NOT NULL,
                    rule_id TEXT,
                    suggestion TEXT,
                    accepted BOOLEAN,
                    actually_fixed BOOLEAN,
                    reward REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES analyzed_projects(id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fb_accepted ON analysis_feedback(accepted)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fb_type ON analysis_feedback(issue_type)")

            # ML weights para analyzer
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analyzer_ml_weights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_type TEXT NOT NULL,
                    metric_key TEXT NOT NULL,
                    metric_value REAL DEFAULT 0.0,
                    json_data TEXT DEFAULT '{}',
                    sample_count INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(metric_type, metric_key)
                )
            """)

            # Métricas globais
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT UNIQUE NOT NULL,
                    metric_value REAL DEFAULT 0.0,
                    json_data TEXT DEFAULT '{}',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ============================================
            # TABELAS DE PREFERÊNCIAS
            # ============================================

            # Preferências do usuário
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    preference_key TEXT UNIQUE NOT NULL,
                    preference_value TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    sample_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ============================================
            # TABELAS DE CONFIGURAÇÃO
            # ============================================

            # Configurações do sistema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_key TEXT UNIQUE NOT NULL,
                    config_value TEXT NOT NULL,
                    description TEXT,
                    is_dangerous BOOLEAN DEFAULT FALSE,
                    requires_confirmation BOOLEAN DEFAULT FALSE,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Marcar schema como aplicado
            cursor.execute("""
                INSERT OR REPLACE INTO db_meta (key, value, updated_at)
                VALUES ('schema_version', ?, CURRENT_TIMESTAMP)
            """, (str(self.SCHEMA_VERSION),))

    # ============================================
    # MÉTODOS DE CONVERSAS
    # ============================================

    def log_conversation(self, session_id: str, role: str, message: str,
                        action: str = None, target: str = None, result: str = None):
        """Registra uma mensagem na conversa."""
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO conversations (session_id, role, message, action, target, result)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_id, role, message, action, target, result))

    def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Retorna histórico de conversa."""
        with self._conn() as conn:
            cursor = conn.execute("""
                SELECT role, message, action, target, result, created_at
                FROM conversations
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (session_id, limit))
            return [dict(row) for row in cursor.fetchall()]

    def set_context(self, session_id: str, key: str, value: str, expires_at: datetime = None):
        """Define uma variável de contexto."""
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO conversation_context (session_id, key, value, expires_at)
                VALUES (?, ?, ?, ?)
            """, (session_id, key, value, expires_at))

    def get_context(self, session_id: str, key: str) -> Optional[str]:
        """Obtém uma variável de contexto."""
        with self._conn() as conn:
            cursor = conn.execute("""
                SELECT value FROM conversation_context
                WHERE session_id = ? AND key = ?
                AND (expires_at IS NULL OR expires_at > datetime('now'))
            """, (session_id, key))
            row = cursor.fetchone()
            return row[0] if row else None

    # ============================================
    # MÉTODOS DE MEMÓRIA
    # ============================================

    def set_memory(self, category: str, key: str, value: str, context: str = None, confidence: float = 1.0):
        """Define um valor na memória persistente."""
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO user_memory (category, key, value, context, confidence, use_count)
                VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(category, key) DO UPDATE SET
                    value = excluded.value,
                    context = COALESCE(excluded.context, context),
                    confidence = (confidence * use_count + excluded.confidence) / (use_count + 1),
                    use_count = use_count + 1,
                    updated_at = CURRENT_TIMESTAMP
            """, (category, key, value, context, confidence))

    def get_memory(self, category: str, key: str) -> Optional[Dict]:
        """Obtém um valor da memória."""
        with self._conn() as conn:
            cursor = conn.execute("""
                SELECT key, value, context, confidence, use_count, updated_at
                FROM user_memory
                WHERE category = ? AND key = ?
            """, (category, key))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_memories_by_category(self, category: str) -> List[Dict]:
        """Retorna todas as memórias de uma categoria."""
        with self._conn() as conn:
            cursor = conn.execute("""
                SELECT key, value, context, confidence, use_count, updated_at
                FROM user_memory
                WHERE category = ?
                ORDER BY use_count DESC, updated_at DESC
            """, (category,))
            return [dict(row) for row in cursor.fetchall()]

    def search_memories(self, query: str, category: str = None) -> List[Dict]:
        """Busca memórias por texto."""
        with self._conn() as conn:
            if category:
                cursor = conn.execute("""
                    SELECT key, value, context, confidence, use_count
                    FROM user_memory
                    WHERE category = ? AND (key LIKE ? OR value LIKE ?)
                    ORDER BY confidence DESC
                """, (category, f'%{query}%', f'%{query}%'))
            else:
                cursor = conn.execute("""
                    SELECT category, key, value, context, confidence, use_count
                    FROM user_memory
                    WHERE key LIKE ? OR value LIKE ?
                    ORDER BY confidence DESC
                """, (f'%{query}%', f'%{query}%'))
            return [dict(row) for row in cursor.fetchall()]

    # ============================================
    # MÉTODOS DE FEEDBACK
    # ============================================

    def log_feedback(self, action: str, reward_type: str, reward_value: float,
                    context: str = None, command: str = None, result: str = None,
                    success: bool = None, rating: int = None):
        """Registra feedback de uma ação."""
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO action_feedback (action, reward_type, reward_value, context, command, result, success, rating)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (action, reward_type, reward_value, context, command, result, success, rating))

    def get_feedback_history(self, action: str = None, limit: int = 100) -> List[Dict]:
        """Retorna histórico de feedback."""
        with self._conn() as conn:
            if action:
                cursor = conn.execute("""
                    SELECT action, reward_type, reward_value, context, success, rating, created_at
                    FROM action_feedback
                    WHERE action = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (action, limit))
            else:
                cursor = conn.execute("""
                    SELECT action, reward_type, reward_value, context, success, rating, created_at
                    FROM action_feedback
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    # ============================================
    # MÉTODOS DE AÇÕES
    # ============================================

    def log_action(self, action: str, target: str = None, parameters: dict = None,
                  result: str = None, success: bool = None, execution_time_ms: int = None,
                  error: str = None):
        """Registra uma ação executada."""
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO action_history (action, target, parameters, result, success, execution_time_ms, error)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (action, target, str(parameters) if parameters else None,
                  result, success, execution_time_ms, error))

    def get_action_stats(self, action: str) -> Dict:
        """Retorna estatísticas de uma ação."""
        with self._conn() as conn:
            cursor = conn.execute("""
                SELECT action, total_score, use_count, success_count, failure_count,
                       avg_score, success_rate, last_reward_at, last_used_at
                FROM rl_action_stats
                WHERE action = ?
            """, (action,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_top_actions(self, limit: int = 10) -> List[Dict]:
        """Retorna ações mais usadas/pontuadas."""
        with self._conn() as conn:
            cursor = conn.execute("""
                SELECT action, total_score, use_count, success_rate, avg_score
                FROM rl_action_stats
                ORDER BY total_score DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    # ============================================
    # MÉTODOS DE RL
    # ============================================

    def update_rl_stats(self, action: str, reward_value: float, success: bool):
        """Atualiza estatísticas de RL para uma ação."""
        with self._conn() as conn:
            cursor = conn.execute("SELECT use_count, success_count FROM rl_action_stats WHERE action = ?", (action,))
            row = cursor.fetchone()

            if row:
                use_count, success_count = row
                new_use = use_count + 1
                new_success = success_count + (1 if success else 0)
                new_total = (row[0] or 0) + reward_value if row else reward_value
                new_avg = new_total / new_use
                new_rate = new_success / new_use

                conn.execute("""
                    UPDATE rl_action_stats SET
                        total_score = ?,
                        use_count = ?,
                        success_count = ?,
                        failure_count = failure_count + ?,
                        avg_score = ?,
                        success_rate = ?,
                        last_reward_at = CURRENT_TIMESTAMP,
                        last_used_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE action = ?
                """, (new_total, new_use, new_success, 0 if success else 1, new_avg, new_rate, action))
            else:
                conn.execute("""
                    INSERT INTO rl_action_stats (action, total_score, use_count, success_count, avg_score, success_rate)
                    VALUES (?, ?, 1, ?, ?, ?)
                """, (action, reward_value, 1 if success else 0, reward_value, 1.0 if success else 0.0))

    def update_rl_context(self, context: str, action: str, reward_value: float, success: bool):
        """Atualiza score de contexto para RL."""
        if not context:
            return
        with self._conn() as conn:
            cursor = conn.execute("""
                INSERT INTO rl_context_scores (context, action, score, use_count, success_count)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(context, action) DO UPDATE SET
                    score = score + excluded.score,
                    use_count = use_count + 1,
                    success_count = success_count + excluded.success_count,
                    last_updated = CURRENT_TIMESTAMP
            """, (context, action, reward_value, 1 if success else 0))

    def get_best_action_for_context(self, context: str, available_actions: List[str] = None) -> Dict:
        """Retorna melhor ação para um contexto."""
        with self._conn() as conn:
            if available_actions:
                placeholders = ','.join(['?' for _ in available_actions])
                cursor = conn.execute(f"""
                    SELECT cs.action, cs.score, cs.use_count,
                           CAST(cs.success_count AS REAL) / CAST(cs.use_count AS REAL) as success_rate,
                           COALESCE(rs.total_score, 0) as global_score
                    FROM rl_context_scores cs
                    LEFT JOIN rl_action_stats rs ON cs.action = rs.action
                    WHERE cs.context = ? AND cs.action IN ({placeholders})
                    ORDER BY cs.score DESC
                    LIMIT 5
                """, (context, *available_actions))
            else:
                cursor = conn.execute("""
                    SELECT cs.action, cs.score, cs.use_count,
                           CAST(cs.success_count AS REAL) / CAST(cs.use_count AS REAL) as success_rate,
                           COALESCE(rs.total_score, 0) as global_score
                    FROM rl_context_scores cs
                    LEFT JOIN rl_action_stats rs ON cs.action = rs.action
                    WHERE cs.context = ?
                    ORDER BY cs.score DESC
                    LIMIT 5
                """, (context,))

            rows = cursor.fetchall()
            if not rows:
                return self._get_best_global_action(conn, available_actions)

            best = rows[0]
            combined = (best[1] * 1.5) + (best[4] * 0.5)
            return {
                "action": best[0],
                "score": round(best[1], 2),
                "use_count": best[2],
                "success_rate": round(best[3], 2) if best[3] else 0,
                "source": "context",
                "combined_score": round(combined, 2)
            }

    def _get_best_global_action(self, conn, available_actions: List[str] = None) -> Dict:
        """Fallback para melhor ação global."""
        if available_actions:
            placeholders = ','.join(['?' for _ in available_actions])
            cursor = conn.execute(f"""
                SELECT action, total_score, use_count, success_rate
                FROM rl_action_stats
                WHERE action IN ({placeholders})
                ORDER BY total_score DESC
                LIMIT 1
            """, (*available_actions,))
        else:
            cursor = conn.execute("""
                SELECT action, total_score, use_count, success_rate
                FROM rl_action_stats
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

    # ============================================
    # MÉTODOS DE ESTATÍSTICAS
    # ============================================

    def increment_usage(self, action: str, execution_time_ms: int = None, success: bool = True):
        """Incrementa contador de uso de uma ação."""
        today = datetime.now().strftime('%Y-%m-%d')
        hour = datetime.now().hour

        with self._conn() as conn:
            conn.execute("""
                INSERT INTO usage_stats (date, hour, action, count, avg_execution_time_ms, success_count, failure_count)
                VALUES (?, ?, ?, 1, ?, ?, ?)
                ON CONFLICT(date, hour, action) DO UPDATE SET
                    count = count + 1,
                    avg_execution_time_ms = COALESCE(
                        (avg_execution_time_ms * count + ?) / (count + 1),
                        avg_execution_time_ms
                    ),
                    success_count = success_count + ?,
                    failure_count = failure_count + ?
            """, (today, hour, action, execution_time_ms,
                  1 if success else 0, 0 if success else 0, 0 if success else 1))

    def get_usage_summary(self, days: int = 7) -> Dict:
        """Retorna resumo de uso."""
        with self._conn() as conn:
            cursor = conn.execute("""
                SELECT
                    SUM(count) as total_actions,
                    COUNT(DISTINCT action) as unique_actions,
                    SUM(success_count) as total_success,
                    SUM(failure_count) as total_failure
                FROM usage_stats
                WHERE date >= date('now', '-' || ? || ' days')
            """, (days,))
            row = cursor.fetchone()
            return dict(row) if row else {}

    def get_daily_stats(self, date: str) -> List[Dict]:
        """Retorna estatísticas por hora para um dia."""
        with self._conn() as conn:
            cursor = conn.execute("""
                SELECT hour, action, count, success_count, failure_count
                FROM usage_stats
                WHERE date = ?
                ORDER BY hour, action
            """, (date,))
            return [dict(row) for row in cursor.fetchall()]

    # ============================================
    # MÉTODOS DE PREFERÊNCIAS
    # ============================================

    def set_preference(self, key: str, value: str, confidence: float = 0.5):
        """Define uma preferência."""
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO user_preferences (preference_key, preference_value, confidence, sample_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(preference_key) DO UPDATE SET
                    preference_value = excluded.preference_value,
                    confidence = (confidence * sample_count + excluded.confidence) / (sample_count + 1),
                    sample_count = sample_count + 1,
                    updated_at = CURRENT_TIMESTAMP
            """, (key, value, confidence))

    def get_preference(self, key: str) -> Optional[str]:
        """Obtém uma preferência."""
        with self._conn() as conn:
            cursor = conn.execute("SELECT preference_value FROM user_preferences WHERE preference_key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None

    # ============================================
    # MÉTODOS DE CONFIGURAÇÃO
    # ============================================

    def register_dangerous_action(self, action: str, requires_confirmation: bool = True):
        """Registra uma ação perigosa."""
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO system_config (config_key, config_value, is_dangerous, requires_confirmation)
                VALUES (?, ?, TRUE, ?)
                ON CONFLICT(config_key) DO UPDATE SET
                    is_dangerous = TRUE,
                    requires_confirmation = excluded.requires_confirmation,
                    updated_at = CURRENT_TIMESTAMP
            """, (action, action, requires_confirmation))

    def is_dangerous_action(self, action: str) -> bool:
        """Verifica se uma ação é perigosa."""
        with self._conn() as conn:
            cursor = conn.execute("""
                SELECT requires_confirmation FROM system_config
                WHERE config_key = ? AND is_dangerous = TRUE
            """, (action,))
            row = cursor.fetchone()
            return row is not None

    def needs_confirmation(self, action: str) -> bool:
        """Verifica se uma ação precisa de confirmação."""
        with self._conn() as conn:
            cursor = conn.execute("""
                SELECT requires_confirmation FROM system_config
                WHERE config_key = ?
            """, (action,))
            row = cursor.fetchone()
            return row and row[0]

    # ============================================
    # EXPORTAÇÃO E BACKUP
    # ============================================

    def export_all(self) -> Dict:
        """Exporta todos os dados para backup."""
        with self._conn() as conn:
            export = {}

            # Exportar stats
            cursor = conn.execute("SELECT * FROM rl_action_stats")
            export['action_stats'] = [dict(row) for row in cursor.fetchall()]

            # Exportar contextos
            cursor = conn.execute("SELECT * FROM rl_context_scores")
            export['context_scores'] = [dict(row) for row in cursor.fetchall()]

            # Exportar preferências
            cursor = conn.execute("SELECT * FROM user_preferences")
            export['preferences'] = [dict(row) for row in cursor.fetchall()]

            # Exportar memórias
            cursor = conn.execute("SELECT * FROM user_memory")
            export['memories'] = [dict(row) for row in cursor.fetchall()]

            export['exported_at'] = datetime.now().isoformat()
            return export


# Instância global
_db = None


def get_jarvis_db() -> JarvisDB:
    """Retorna instância global do banco."""
    global _db
    if _db is None:
        _db = JarvisDB()
    return _db