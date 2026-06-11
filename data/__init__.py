"""
Data Layer - Camada de dados para o Jarvis MiniMax
Arquitetura RAG-Ready
"""

from .database import db, Database
from .vector_store import VectorStore, ConversationStore, CommandStore, KnowledgeStore
from .memory import (
    memory_manager,
    short_term_memory,
    long_term_memory,
    MemoryManager,
    ShortTermMemory,
    LongTermMemory
)
from .rag import rag_retriever, context_builder, RAGRetriever, ContextBuilder
from .rl_database import JarvisDatabase, get_database
from .core_database import JarvisDB, get_jarvis_db

__all__ = [
    # Database
    "db",
    "Database",
    # Core Database (unified schema)
    "JarvisDB",
    "get_jarvis_db",
    # Vector Store
    "VectorStore",
    "ConversationStore",
    "CommandStore",
    "KnowledgeStore",
    # Memory
    "memory_manager",
    "short_term_memory",
    "long_term_memory",
    "MemoryManager",
    "ShortTermMemory",
    "LongTermMemory",
    # RAG
    "rag_retriever",
    "context_builder",
    "RAGRetriever",
    "ContextBuilder",
    # RL Database (legacy)
    "JarvisDatabase",
    "get_database",
]