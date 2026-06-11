"""
Advanced Context Builder - Contexto Avançado para prompts
Combina workspace, short-term, long-term e RAG para construir
contexto rico para envio à MiniMax.
"""

import json
from datetime import datetime
from typing import List, Dict, Optional, Any

from .workspace_memory import (
    workspace_memory, conversation_summarizer,
    WorkspaceMemory, ConversationSummarizer
)
from .memory import memory_manager, short_term_memory, long_term_memory
from .vector_store import ConversationStore, CommandStore, KnowledgeStore
from .core_database import get_jarvis_db


class RetrievedContext:
    """Contexto recuperado para RAG."""
    def __init__(self, content: str, source: str, score: float, metadata: Dict = None):
        self.content = content
        self.source = source
        self.score = score
        self.metadata = metadata or {}


class RAGRetriever:
    """
    Sistema de Retrieval-Augmented Generation.
    Combina múltiplas fontes de dados para enriquecer prompts.
    """

    def __init__(self):
        self.conversation_store = ConversationStore()
        self.command_store = CommandStore()
        self.knowledge_store = KnowledgeStore()

    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedContext]:
        """Recupera contextos relevantes de todas as fontes."""
        results = []

        # Busca em conversas
        conv_results = self.conversation_store.search_conversation(query, top_k)
        for r in conv_results:
            results.append(RetrievedContext(
                content=r.get("user_input", ""),
                source="conversation",
                score=r.get("score", 0),
                metadata=r
            ))

        # Busca em comandos
        cmd_results = self.command_store.search_commands(query, top_k)
        for r in cmd_results:
            results.append(RetrievedContext(
                content=r.get("text", ""),
                source="command",
                score=r.get("score", 0),
                metadata=r
            ))

        # Busca em conhecimento
        kn_results = self.knowledge_store.search_knowledge(query, top_k)
        for r in kn_results:
            results.append(RetrievedContext(
                content=r.get("text", ""),
                source="knowledge",
                score=r.get("score", 0),
                metadata=r
            ))

        # Busca em memória
        mem_results = memory_manager.search(query, limit=top_k)
        for item in mem_results:
            results.append(RetrievedContext(
                content=item.content,
                source="memory",
                score=0.5,
                metadata={"importance": item.importance, "tags": item.tags}
            ))

        # Ordena por score
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def build_context(self, query: str, max_chars: int = 2000) -> str:
        """Constrói uma string de contexto para adicionar ao prompt."""
        retrieved = self.retrieve(query)

        if not retrieved:
            return ""

        context_parts = ["=== Contexto Recuperado ==="]
        current_len = 0

        for item in retrieved:
            if current_len + len(item.content) > max_chars:
                break
            context_parts.append(f"\n[{item.source.upper()}] {item.content}")
            current_len += len(item.content)

        return "\n".join(context_parts)

    def log_interaction(self, user_input: str, assistant_response: str,
                       action: str = "", success: bool = True):
        """Registra uma interação para futuras recuperações."""
        self.conversation_store.add_exchange(
            user_input, assistant_response, action, success
        )

    def log_command(self, command: str, action: str, target: str = "",
                    result: str = "", success: bool = True):
        """Registra um comando para futuras recuperações."""
        self.command_store.add_command(
            command, action, target, result, success
        )

    def add_knowledge(self, content: str, category: str = "",
                      tags: Optional[List[str]] = None):
        """Adiciona conhecimento à base."""
        self.knowledge_store.add_knowledge(content, category, tags)

    def get_stats(self) -> Dict[str, int]:
        """Retorna estatísticas do sistema RAG."""
        return {
            "conversations": self.conversation_store.count(),
            "commands": self.command_store.count(),
            "knowledge": self.knowledge_store.count(),
            **memory_manager.get_stats()
        }


class AdvancedContextBuilder:
    """
    Context Builder Avançado que combina:
    - Histórico recente de conversas
    - Memória persistente
    - Preferências do usuário
    - Workspace ativo
    - Resumos de conversas anteriores
    - Contexto RAG (vector store)
    """

    def __init__(self):
        self.workspace_memory: WorkspaceMemory = workspace_memory
        self.memory_manager = memory_manager
        self.short_term = short_term_memory
        self.long_term = long_term_memory
        self.rag = RAGRetriever()
        self.summarizer: ConversationSummarizer = conversation_summarizer
        self.db = get_jarvis_db()

    def build(self, query: str = "",
              include_workspace: bool = True,
              include_short_term: bool = True,
              include_long_term: bool = True,
              include_rag: bool = True,
              max_chars: int = 3000) -> str:
        """
        Constrói contexto completo para um prompt.

        Args:
            query: Query atual do usuário (para buscar contexto relevante)
            include_workspace: Incluir contexto do workspace ativo
            include_short_term: Incluir conversa recente
            include_long_term: Incluir fatos e memórias de longo prazo
            include_rag: Incluir contexto do RAG
            max_chars: Máximo de caracteres no contexto final
        """
        parts = []
        query_lower = query.lower() if query else ""

        # 1. Workspace Context (se ativo)
        if include_workspace:
            ws = self.workspace_memory.get_active_workspace()
            if ws:
                workspace_ctx = self._build_workspace_context(ws.id, query_lower)
                if workspace_ctx:
                    parts.append(workspace_ctx)

        # 2. Short-term (últimos turnos)
        if include_short_term:
            recent = self.short_term.get_conversation_text(turns=5)
            if recent:
                parts.append(f"=== Conversa Recente ===\n{recent}")

        # 3. Long-term facts
        if include_long_term:
            facts = self.long_term.get_all_facts()
            if facts:
                parts.append(self._format_facts(facts))

            # Memórias de longo prazo relevantes
            if query_lower:
                mem_context = self.memory_manager.get_context(query_lower, max_items=3)
                if mem_context:
                    parts.append(mem_context)

        # 4. RAG context
        if include_rag and query_lower:
            rag_ctx = self.rag.build_context(query_lower, max_chars=1500)
            if rag_ctx:
                parts.append(rag_ctx)

        if not parts:
            return ""

        # Combinar e truncar
        return self._combine_and_truncate(parts, max_chars)

    def _build_workspace_context(self, workspace_id: int, query: str = "") -> str:
        """Constrói contexto específico do workspace."""
        ws = self.workspace_memory.get_workspace_by_id(workspace_id)
        if not ws:
            return ""

        parts = [f"=== Workspace: {ws.name} ==="]

        if ws.description:
            parts.append(f"Descrição: {ws.description}")

        # Tarefas pendentes
        pending = self.workspace_memory.get_pending_tasks(workspace_id)
        if pending:
            parts.append(f"\nTarefas pendentes ({len(pending)}):")
            for task in pending[:5]:
                status_icon = "🔴" if task.status == "pending" else "🟡"
                parts.append(f"  {status_icon} [{task.priority}] {task.title}")

        # Últimas ações
        recent = self.workspace_memory.get_recent_actions(workspace_id, limit=5)
        if recent:
            parts.append("\nÚltimas ações:")
            for action in recent:
                desc = action.description[:60] if action.description else ""
                parts.append(f"  - {action.action}: {desc}")

        # Última análise
        last_analysis = self.workspace_memory.get_last_analysis(workspace_id)
        if last_analysis:
            parts.append(f"\nÚltima análise ({last_analysis.created_at[:10]}):")
            parts.append(f"  Score: {last_analysis.score}/100, Issues: {last_analysis.issues_count}")

        return "\n".join(parts)

    def _format_facts(self, facts: Dict[str, Any]) -> str:
        """Formata fatos importantes."""
        parts = ["=== Fatos Importantes ==="]
        for key, value in facts.items():
            if isinstance(value, dict):
                value = value.get('value', value)
            parts.append(f"- {key}: {value}")
        return "\n".join(parts)

    def _combine_and_truncate(self, parts: List[str], max_chars: int) -> str:
        """Combina partes do contexto e trunca se necessário."""
        combined = "\n\n".join(parts)

        if len(combined) <= max_chars:
            return combined

        # Truncar do final para o início (prioridade)
        truncated = combined[:max_chars]
        last_newline = truncated.rfind("\n\n")

        if last_newline > max_chars * 0.7:
            truncated = truncated[:last_newline]

        return truncated + "\n...(contexto truncado)"

    def build_for_minimax(self, query: str, session_id: str = None) -> str:
        """
        Constrói contexto otimizado para envio à MiniMax.
        Inclui workspace, resumos de conversas anteriores e contexto RAG.
        """
        context = self.build(query=query, max_chars=2500)

        # Adicionar resumo de conversa anterior da sessão, se existir
        if session_id:
            summary = self.summarizer.get_recent_summary(session_id)
            if summary:
                context = f"=== Resumo da Conversa Anterior ===\n{summary}\n\n{context}"

        return context

    def answer_project_question(self, question: str) -> str:
        """
        Responde perguntas sobre o projeto:
        - 'onde parei?' → último estado + tarefas pendentes
        - 'o que fiz ontem?' → ações de ontem
        - 'problemas frequentes?' → issues recorrentes
        - 'última análise?' → última análise do projeto
        """
        ws = self.workspace_memory.get_active_workspace()
        if not ws:
            return "Nenhum workspace ativo. Crie ou ative um workspace primeiro."

        question_lower = question.lower()

        if any(p in question_lower for p in ["onde parei", "onde eu parei", "último estado"]):
            return self.workspace_memory.get_where_i_left_off(ws.id)

        elif any(p in question_lower for p in ["ontem", "o que fiz ontem", "ações de ontem"]):
            return self.workspace_memory.get_yesterday_summary(ws.id)

        elif any(p in question_lower for p in ["problema", "erro recorrente", "frequente", "repetitivo"]):
            return self.workspace_memory.get_recurring_problems(ws.id)

        elif any(p in question_lower for p in ["última análise", "análise", "último scan"]):
            last_analysis = self.workspace_memory.get_last_analysis(ws.id)
            if last_analysis:
                parts = [
                    f"📊 Última Análise ({last_analysis.created_at[:10]}):",
                    f"   Tipo: {last_analysis.analysis_type}",
                    f"   Score: {last_analysis.score}/100",
                    f"   Issues encontrados: {last_analysis.issues_count}",
                    f"   Sugestões aceitas: {last_analysis.suggestions_accepted}",
                    f"   Sugestões rejeitadas: {last_analysis.suggestions_rejected}",
                ]
                if last_analysis.issues_summary:
                    parts.append("\n   Principais issues:")
                    for issue in last_analysis.issues_summary[:3]:
                        parts.append(f"   - {issue.get('message', str(issue))}")
                return "\n".join(parts)
            return "Nenhuma análise registrada para este workspace."

        elif any(p in question_lower for p in ["tarefa", "pendente", "a fazer", "todo"]):
            pending = self.workspace_memory.get_pending_tasks(ws.id)
            if not pending:
                return "Nenhuma tarefa pendente neste workspace."
            parts = [f"📋 Tarefas pendentes ({len(pending)}):"]
            for task in pending:
                priority = "🔴" if task.priority <= 2 else "🟡" if task.priority == 3 else "🟢"
                parts.append(f"  {priority} {task.title}")
            return "\n".join(parts)

        elif any(p in question_lower for p in ["workspace", "projeto atual", "qual projeto"]):
            return self.workspace_memory.get_workspace_context()

        else:
            return f"Não entendi a pergunta sobre o workspace. Tente: 'onde parei?', 'o que fiz ontem?', 'problemas frequentes?' ou 'última análise?'"

    def log_action_to_workspace(self, action: str, description: str = "",
                                details: dict = None, session_id: str = None):
        """Loga ação executada no workspace ativo."""
        ws = self.workspace_memory.get_active_workspace()
        if ws:
            self.workspace_memory.log_action(
                workspace_id=ws.id,
                action=action,
                description=description,
                details=details,
                session_id=session_id
            )

    def check_and_summarize(self, session_id: str) -> bool:
        """Verifica se deve resumir e salva resumo se necessário."""
        if self.summarizer.should_summarize():
            ws = self.workspace_memory.get_active_workspace()
            if ws:
                turns = self.short_term.conversation_history
                if turns:
                    self.summarizer.save_summary(ws.id, session_id, turns)
                    self.summarizer.reset_counter()
                    return True
        return False


# Instância global
context_builder = AdvancedContextBuilder()