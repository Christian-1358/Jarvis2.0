"""
Workspace Memory - Sistema de memória por projeto/workspace
Permite que o Jarvis mantenha contexto persistente entre sessões
e acompanhe a evolução dos projetos ao longo do tempo.
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from .core_database import get_jarvis_db


@dataclass
class Workspace:
    """Workspace/projeto."""
    id: int
    name: str
    description: str
    project_path: str
    is_active: bool
    created_at: str
    updated_at: str


@dataclass
class Task:
    """Tarefa do workspace."""
    id: int
    workspace_id: int
    title: str
    description: str
    status: str
    priority: int
    created_at: str
    updated_at: str
    completed_at: Optional[str]


@dataclass
class TrackedFile:
    """Arquivo rastreado."""
    id: int
    workspace_id: int
    file_path: str
    file_type: str
    last_modified: str
    last_analyzed: Optional[str]
    analysis_summary: Optional[str]
    issues_count: int


@dataclass
class HistoryEntry:
    """Entrada de histórico."""
    id: int
    workspace_id: int
    action: str
    description: str
    details: Optional[Dict]
    session_id: Optional[str]
    created_at: str


@dataclass
class Analysis:
    """Análise de projeto."""
    id: int
    workspace_id: int
    analysis_type: str
    score: float
    issues_count: int
    issues_summary: Optional[List[Dict]]
    suggestions_accepted: int
    suggestions_rejected: int
    created_at: str


@dataclass
class ConversationSummary:
    """Resumo de conversa."""
    id: int
    workspace_id: Optional[int]
    session_id: str
    summary_text: str
    key_topics: Optional[List[str]]
    decisions: Optional[List[str]]
    next_steps: Optional[str]
    created_at: str


class WorkspaceMemory:
    """
    Gerenciador de memória por workspace/projeto.
    Mantém contexto persistente entre sessões.
    """

    def __init__(self):
        self.db = get_jarvis_db()
        self._active_workspace: Optional[Workspace] = None
        self._load_active_workspace()

    def _load_active_workspace(self):
        """Carrega workspace ativo."""
        ws = self.db.get_active_workspace()
        if ws:
            self._active_workspace = Workspace(**ws)

    def _row_to_workspace(self, row: Dict) -> Workspace:
        """Converte row para Workspace."""
        return Workspace(**row)

    def _row_to_task(self, row: Dict) -> Task:
        """Converte row para Task."""
        return Task(**row)

    def _row_to_tracked_file(self, row: Dict) -> TrackedFile:
        """Converte row para TrackedFile."""
        return TrackedFile(**row)

    def _row_to_history_entry(self, row: Dict) -> HistoryEntry:
        """Converte row para HistoryEntry."""
        details = None
        if row.get('details'):
            try:
                details = json.loads(row['details'])
            except (json.JSONDecodeError, TypeError):
                details = row['details']
        return HistoryEntry(
            details=details,
            **{k: v for k, v in row.items() if k != 'details'}
        )

    def _row_to_analysis(self, row: Dict) -> Analysis:
        """Converte row para Analysis."""
        issues_summary = None
        if row.get('issues_summary'):
            try:
                issues_summary = json.loads(row['issues_summary'])
            except (json.JSONDecodeError, TypeError):
                issues_summary = row['issues_summary']
        return Analysis(
            issues_summary=issues_summary,
            **{k: v for k, v in row.items() if k != 'issues_summary'}
        )

    # ============================================
    # Workspace Management
    # ============================================

    def create_workspace(self, name: str, description: str = "",
                        project_path: str = None) -> int:
        """Cria um novo workspace."""
        ws_id = self.db.create_workspace(name, description, project_path)
        return ws_id

    def get_workspace(self, name: str) -> Optional[Workspace]:
        """Obtém workspace pelo nome."""
        row = self.db.get_workspace(name)
        return self._row_to_workspace(row) if row else None

    def get_workspace_by_id(self, workspace_id: int) -> Optional[Workspace]:
        """Obtém workspace pelo ID."""
        row = self.db.get_workspace_by_id(workspace_id)
        return self._row_to_workspace(row) if row else None

    def set_active_workspace(self, name: str) -> bool:
        """Define workspace ativo."""
        ws = self.get_workspace(name)
        if not ws:
            return False
        self.db.set_active_workspace(name)
        self._active_workspace = ws
        return True

    def get_active_workspace(self) -> Optional[Workspace]:
        """Retorna workspace ativo."""
        return self._active_workspace

    def list_workspaces(self) -> List[Workspace]:
        """Lista todos os workspaces."""
        rows = self.db.list_workspaces()
        return [self._row_to_workspace(row) for row in rows]

    def refresh_active_workspace(self):
        """Recarrega workspace ativo do banco."""
        self._load_active_workspace()

    # ============================================
    # Task Management
    # ============================================

    def add_task(self, workspace_id: int, title: str,
                description: str = "", priority: int = 3) -> int:
        """Adiciona tarefa ao workspace."""
        return self.db.add_workspace_task(workspace_id, title, description, priority)

    def get_pending_tasks(self, workspace_id: int) -> List[Task]:
        """Retorna tarefas pendentes do workspace."""
        rows = self.db.get_workspace_tasks(workspace_id, status='pending')
        return [self._row_to_task(row) for row in rows]

    def get_all_tasks(self, workspace_id: int) -> List[Task]:
        """Retorna todas as tarefas do workspace."""
        rows = self.db.get_workspace_tasks(workspace_id)
        return [self._row_to_task(row) for row in rows]

    def get_tasks_by_status(self, workspace_id: int, status: str) -> List[Task]:
        """Retorna tarefas por status."""
        rows = self.db.get_workspace_tasks(workspace_id, status=status)
        return [self._row_to_task(row) for row in rows]

    def complete_task(self, task_id: int) -> bool:
        """Marca tarefa como completada."""
        return self.db.update_task_status(task_id, 'completed')

    def update_task_status(self, task_id: int, status: str) -> bool:
        """Atualiza status de tarefa."""
        return self.db.update_task_status(task_id, status)

    # ============================================
    # File Tracking
    # ============================================

    def track_file(self, workspace_id: int, file_path: str,
                  file_type: str = "") -> int:
        """Rastreia arquivo no workspace."""
        return self.db.track_workspace_file(workspace_id, file_path, file_type)

    def get_tracked_files(self, workspace_id: int) -> List[TrackedFile]:
        """Retorna arquivos rastreados do workspace."""
        rows = self.db.get_workspace_files(workspace_id)
        return [self._row_to_tracked_file(row) for row in rows]

    def update_file_analysis(self, file_id: int, summary: str,
                            issues_count: int) -> bool:
        """Atualiza análise de arquivo."""
        self.db.update_file_analysis(file_id, summary, issues_count)
        return True

    # ============================================
    # History
    # ============================================

    def log_action(self, workspace_id: int, action: str,
                  description: str = "", details: dict = None,
                  session_id: str = None) -> bool:
        """Registra ação no workspace."""
        self.db.log_workspace_action(workspace_id, action, description,
                                     details, session_id)
        return True

    def get_recent_actions(self, workspace_id: int,
                          limit: int = 20) -> List[HistoryEntry]:
        """Retorna ações recentes do workspace."""
        rows = self.db.get_workspace_history(workspace_id, limit)
        return [self._row_to_history_entry(row) for row in rows]

    def get_actions_by_date(self, workspace_id: int,
                           date: str) -> List[HistoryEntry]:
        """Retorna ações do workspace para uma data."""
        rows = self.db.get_workspace_history_by_date(workspace_id, date)
        return [self._row_to_history_entry(row) for row in rows]

    def get_yesterday_actions(self, workspace_id: int) -> List[HistoryEntry]:
        """Retorna ações de ontem do workspace."""
        rows = self.db.get_workspace_yesterday_actions(workspace_id)
        return [self._row_to_history_entry(row) for row in rows]

    # ============================================
    # Analysis
    # ============================================

    def save_analysis(self, workspace_id: int, analysis_type: str,
                     score: float, issues: list = None,
                     suggestions_accepted: int = 0,
                     suggestions_rejected: int = 0) -> int:
        """Salva análise de workspace."""
        return self.db.save_workspace_analysis(
            workspace_id, analysis_type, score, issues,
            suggestions_accepted, suggestions_rejected
        )

    def get_last_analysis(self, workspace_id: int) -> Optional[Analysis]:
        """Retorna última análise do workspace."""
        row = self.db.get_last_workspace_analysis(workspace_id)
        return self._row_to_analysis(row) if row else None

    def get_analysis_history(self, workspace_id: int,
                            limit: int = 10) -> List[Analysis]:
        """Retorna histórico de análises."""
        rows = self.db.get_workspace_analysis_history(workspace_id, limit)
        return [self._row_to_analysis(row) for row in rows]

    # ============================================
    # Summaries
    # ============================================

    def save_summary(self, workspace_id: int, session_id: str,
                    summary_text: str, key_topics: list = None,
                    decisions: list = None, next_steps: str = None) -> int:
        """Salva resumo de conversa."""
        return self.db.save_conversation_summary(
            workspace_id, session_id, summary_text,
            key_topics, decisions, next_steps
        )

    def get_summary(self, session_id: str) -> Optional[ConversationSummary]:
        """Retorna resumo de conversa."""
        row = self.db.get_conversation_summary(session_id)
        if not row:
            return None
        topics = None
        decisions = None
        if row.get('key_topics'):
            try:
                topics = json.loads(row['key_topics'])
            except (json.JSONDecodeError, TypeError):
                topics = row['key_topics']
        if row.get('decisions'):
            try:
                decisions = json.loads(row['decisions'])
            except (json.JSONDecodeError, TypeError):
                decisions = row['decisions']
        return ConversationSummary(
            key_topics=topics,
            decisions=decisions,
            **{k: v for k, v in row.items()
               if k not in ('key_topics', 'decisions')}
        )

    def get_workspace_summaries(self, workspace_id: int,
                               limit: int = 10) -> List[ConversationSummary]:
        """Retorna resumos do workspace."""
        rows = self.db.get_workspace_summaries(workspace_id, limit)
        result = []
        for row in rows:
            topics = None
            decisions = None
            if row.get('key_topics'):
                try:
                    topics = json.loads(row['key_topics'])
                except (json.JSONDecodeError, TypeError):
                    topics = row['key_topics']
            if row.get('decisions'):
                try:
                    decisions = json.loads(row['decisions'])
                except (json.JSONDecodeError, TypeError):
                    decisions = row['decisions']
            result.append(ConversationSummary(
                key_topics=topics,
                decisions=decisions,
                **{k: v for k, v in row.items()
                   if k not in ('key_topics', 'decisions')}
            ))
        return result

    # ============================================
    # Recurring Issues
    # ============================================

    def get_recurring_issues(self, workspace_id: int,
                            min_occurrences: int = 2) -> List[Dict]:
        """Retorna issues recorrentes no workspace."""
        return self.db.get_recurring_issues(workspace_id, min_occurrences)

    # ============================================
    # Context Recovery
    # ============================================

    def get_workspace_context(self, query: str = "") -> str:
        """Retorna contexto completo do workspace ativo."""
        ws = self.get_active_workspace()
        if not ws:
            return ""

        parts = [f"=== Workspace: {ws.name} ==="]

        if ws.description:
            parts.append(f"Descrição: {ws.description}")

        # Tarefas pendentes
        pending = self.get_pending_tasks(ws.id)
        if pending:
            parts.append("\nTarefas pendentes:")
            for task in pending[:5]:
                priority_marker = "🔴" if task.priority <= 2 else "🟡" if task.priority == 3 else "🟢"
                parts.append(f"  {priority_marker} [{task.status}] {task.title}")

        # Últimas ações
        recent = self.get_recent_actions(ws.id, limit=5)
        if recent:
            parts.append("\nÚltimas ações:")
            for action in recent:
                parts.append(f"  - {action.action}: {action.description[:50]}...")

        return "\n".join(parts)

    def get_where_i_left_off(self, workspace_id: int) -> str:
        """Retorna estado do projeto (onde parei)."""
        ws = self.get_workspace_by_id(workspace_id)
        if not ws:
            return "Workspace não encontrado."

        parts = [f"📍 Workspace: {ws.name}"]

        # Última análise
        last_analysis = self.get_last_analysis(workspace_id)
        if last_analysis:
            parts.append(f"\n📊 Última análise ({last_analysis.created_at[:10]}):")
            parts.append(f"   Score: {last_analysis.score}/100")
            parts.append(f"   Issues: {last_analysis.issues_count}")

        # Tarefas pendentes
        pending = self.get_pending_tasks(workspace_id)
        if pending:
            parts.append(f"\n📋 Tarefas pendentes ({len(pending)}):")
            for task in pending[:3]:
                parts.append(f"   - {task.title}")

        # Última ação
        recent = self.get_recent_actions(workspace_id, limit=1)
        if recent:
            action = recent[0]
            parts.append(f"\n⏰ Última ação ({action.created_at[:16]}):")
            parts.append(f"   {action.action}: {action.description[:100]}")

        return "\n".join(parts)

    def get_yesterday_summary(self, workspace_id: int) -> str:
        """Retorna resumo do que foi feito ontem."""
        ws = self.get_workspace_by_id(workspace_id)
        if not ws:
            return "Workspace não encontrado."

        yesterday_actions = self.get_yesterday_actions(workspace_id)

        if not yesterday_actions:
            return f"📅 Workspace {ws.name}: Nenhuma ação registrada ontem."

        parts = [f"📅 Resumo de ontem - Workspace: {ws.name}"]
        parts.append(f"Total de ações: {len(yesterday_actions)}")

        # Agrupar por ação
        action_counts: Dict[str, int] = {}
        for action in yesterday_actions:
            action_counts[action.action] = action_counts.get(action.action, 0) + 1

        parts.append("\nAções realizadas:")
        for action, count in sorted(action_counts.items(), key=lambda x: -x[1]):
            parts.append(f"  - {action}: {count}x")

        return "\n".join(parts)

    def get_recurring_problems(self, workspace_id: int) -> str:
        """Retorna problemas recorrentes."""
        issues = self.get_recurring_issues(workspace_id, min_occurrences=2)

        if not issues:
            return "Nenhum problema recorrente detectado."

        parts = ["🔄 Problemas recorrentes:"]
        for issue in issues:
            parts.append(f"  - {issue['action']} ({issue['count']}x): {issue['description'][:60]}...")

        return "\n".join(parts)


class ConversationSummarizer:
    """
    Gerador de resumos automáticos de conversas.
    Reduz tamanho do contexto mantendo informações importantes.
    """

    def __init__(self):
        self.db = get_jarvis_db()
        self.turns_since_last_summary = 0
        self.SUMMARIZE_THRESHOLD = 20  # Resumir a cada 20 turnos

    def should_summarize(self, turns_count: int = None) -> bool:
        """Determina se a conversa deve ser resumida."""
        if turns_count is not None:
            return turns_count >= self.SUMMARIZE_THRESHOLD
        self.turns_since_last_summary += 1
        return self.turns_since_last_summary >= self.SUMMARIZE_THRESHOLD

    def summarize(self, conversation_turns: List[Dict]) -> Dict:
        """
        Gera resumo de uma conversa.
        Extrai tópicos, decisões e próximos passos.
        """
        if not conversation_turns:
            return {"summary": "", "topics": [], "decisions": [], "next_steps": ""}

        # Extrair ações únicas
        actions = set()
        topics = set()
        decisions = []
        next_steps = []

        for turn in conversation_turns:
            content = turn.get('content', '')
            action = turn.get('action', '')

            if action:
                actions.add(action)

            # Heurísticas simples para detectar decisões e próximos passos
            content_lower = content.lower()
            if 'decidi' in content_lower or 'vou usar' in content_lower or 'escolhi' in content_lower:
                decisions.append(content[:100])
            if 'depois' in content_lower or 'próximo' in content_lower or 'futuro' in content_lower:
                next_steps.append(content[:100])

        # Gerar resumo
        summary_parts = [f"Conversa com {len(conversation_turns)} turnos."]
        if actions:
            summary_parts.append(f"Ações: {', '.join(list(actions)[:5])}")
        if decisions:
            summary_parts.append(f"Decisões: {'; '.join(decisions[:3])}")

        return {
            "summary": " ".join(summary_parts),
            "topics": list(topics),
            "decisions": decisions[:5],
            "next_steps": "; ".join(next_steps[:3])
        }

    def save_summary(self, workspace_id: int, session_id: str,
                    conversation_turns: List[Dict]) -> Optional[int]:
        """Salva resumo da conversa no banco."""
        if not conversation_turns:
            return None

        result = self.summarize(conversation_turns)
        if not result["summary"]:
            return None

        return self.db.save_conversation_summary(
            workspace_id=workspace_id,
            session_id=session_id,
            summary_text=result["summary"],
            key_topics=result["topics"],
            decisions=result["decisions"],
            next_steps=result["next_steps"]
        )

    def get_recent_summary(self, session_id: str) -> Optional[str]:
        """Retorna resumo mais recente de uma sessão."""
        row = self.db.get_conversation_summary(session_id)
        if row:
            return row.get('summary_text')
        return None

    def reset_counter(self):
        """Reseta contador de turnos."""
        self.turns_since_last_summary = 0


# Instâncias globais
workspace_memory = WorkspaceMemory()
conversation_summarizer = ConversationSummarizer()