"""
Camada de dados - Sistema RAG (Retrieval-Augmented Generation)
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from .vector_store import ConversationStore, CommandStore, KnowledgeStore
from .memory import memory_manager, short_term_memory, long_term_memory


@dataclass
class RetrievedContext:
    """Contexto recuperado para RAG."""
    content: str
    source: str  # 'conversation', 'command', 'knowledge', 'memory'
    score: float
    metadata: Dict


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
        """
        Recupera contextos relevantes de todas as fontes.
        """
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
                score=0.5,  # Memórias não têm score de similaridade
                metadata={"importance": item.importance, "tags": item.tags}
            ))

        # Ordena por score
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def build_context(self, query: str, max_chars: int = 2000) -> str:
        """
        Constrói uma string de contexto para adicionar ao prompt.
        """
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


class ContextBuilder:
    """
    Construtor de contexto para prompts.
    Combina short-term, long-term e RAG.
    """

    def __init__(self):
        self.rag = RAGRetriever()

    def build(self, query: str, include_short_term: bool = True,
              include_long_term: bool = True,
              include_rag: bool = True) -> str:
        """
        Constrói contexto completo para um prompt.
        """
        parts = []
        query_lower = query.lower()

        # Contexto de conversa recente (short-term)
        if include_short_term:
            recent = short_term_memory.get_conversation_text(turns=5)
            if recent:
                parts.append(f"=== Conversa Recente ===\n{recent}")

        # Fatos importantes (long-term)
        if include_long_term:
            facts = long_term_memory.get_all_facts()
            if facts:
                facts_parts = ["=== Fatos Importantes ==="]
                for key, value in facts.items():
                    facts_parts.append(f"- {key}: {value}")
                parts.append("\n".join(facts_parts))

            # Memórias de longo prazo relevantes
            mem_context = memory_manager.get_context(query_lower, max_items=3)
            if mem_context:
                parts.append(mem_context)

        # Contexto RAG
        if include_rag:
            rag_context = self.rag.build_context(query_lower, max_chars=1500)
            if rag_context:
                parts.append(rag_context)

        if not parts:
            return ""

        return "\n\n".join(parts)

    def add_to_prompt(self, query: str, base_prompt: str,
                      max_context_chars: int = 1500) -> str:
        """
        Adiciona contexto a um prompt base.
        """
        context = self.build(query)
        if not context:
            return base_prompt

        # Limita o tamanho do contexto
        if len(context) > max_context_chars:
            context = context[:max_context_chars] + "\n...(contexto truncado)"

        return f"{base_prompt}\n\n{context}"


# Instâncias globais
rag_retriever = RAGRetriever()
context_builder = ContextBuilder()