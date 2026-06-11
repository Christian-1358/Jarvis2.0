"""
Camada de dados - Sistema de Memória (Short-term e Long-term)
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict

BASE_DIR = Path(__file__).parent.parent
MEMORY_DIR = BASE_DIR / "dados" / "memory"
SHORT_TERM_DIR = MEMORY_DIR / "short_term"
LONG_TERM_DIR = MEMORY_DIR / "long_term"

SHORT_TERM_DIR.mkdir(parents=True, exist_ok=True)
LONG_TERM_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class MemoryItem:
    """Item de memória."""
    id: str
    content: str
    memory_type: str  # 'short_term' ou 'long_term'
    importance: int   # 1-5
    access_count: int
    last_accessed: str
    created_at: str
    tags: List[str]
    metadata: Dict


class MemoryManager:
    """
    Gerenciador de memória do Jarvis.
    - Short-term: memória da sessão atual
    - Long-term: memória persistente entre sessões
    """

    def __init__(self):
        self.short_term: Dict[str, MemoryItem] = {}
        self.long_term: Dict[str, MemoryItem] = {}
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._load_long_term()

    def _load_long_term(self):
        """Carrega memórias de longo prazo do disco."""
        long_term_file = LONG_TERM_DIR / "memories.json"
        if long_term_file.exists():
            try:
                data = json.loads(long_term_file.read_text())
                self.long_term = {
                    k: MemoryItem(**v) for k, v in data.items()
                }
            except (json.JSONDecodeError, TypeError):
                self.long_term = {}

    def _save_long_term(self):
        """Salva memórias de longo prazo no disco."""
        long_term_file = LONG_TERM_DIR / "memories.json"
        data = {k: asdict(v) for k, v in self.long_term.items()}
        long_term_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def _generate_id(self, content: str) -> str:
        """Gera ID único para a memória."""
        import hashlib
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def add(self, content: str, memory_type: str = "short_term",
            importance: int = 3, tags: Optional[List[str]] = None,
            metadata: Optional[Dict] = None) -> str:
        """Adiciona uma memória."""
        memory_id = self._generate_id(content)
        item = MemoryItem(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            access_count=0,
            last_accessed=datetime.now().isoformat(),
            created_at=datetime.now().isoformat(),
            tags=tags or [],
            metadata=metadata or {}
        )

        if memory_type == "long_term":
            self.long_term[memory_id] = item
            self._save_long_term()
        else:
            self.short_term[memory_id] = item

        return memory_id

    def get(self, memory_id: str, memory_type: str = "short_term") -> Optional[MemoryItem]:
        """Retorna uma memória específica."""
        store = self.long_term if memory_type == "long_term" else self.short_term
        item = store.get(memory_id)

        if item:
            item.access_count += 1
            item.last_accessed = datetime.now().isoformat()

        return item

    def search(self, query: str, memory_type: Optional[str] = None,
               limit: int = 10) -> List[MemoryItem]:
        """Busca memórias por similaridade simples."""
        results = []
        query_lower = query.lower()
        stores = [self.long_term] if memory_type == "long_term" else (
            [self.short_term] if memory_type == "short_term" else
            [self.short_term, self.long_term]
        )

        for store in stores:
            for item in store.values():
                if query_lower in item.content.lower():
                    results.append(item)

        results.sort(key=lambda x: (x.importance, x.access_count), reverse=True)
        return results[:limit]

    def promote_to_long_term(self, memory_id: str) -> bool:
        """Promove uma memória de curto para longo prazo."""
        if memory_id in self.short_term:
            item = self.short_term.pop(memory_id)
            item.memory_type = "long_term"
            self.long_term[memory_id] = item
            self._save_long_term()
            return True
        return False

    def delete(self, memory_id: str, memory_type: str = "short_term") -> bool:
        """Remove uma memória."""
        store = self.long_term if memory_type == "long_term" else self.short_term
        if memory_id in store:
            del store[memory_id]
            if memory_type == "long_term":
                self._save_long_term()
            return True
        return False

    def clear_short_term(self):
        """Limpa memórias de curto prazo (fim de sessão)."""
        # Salva as mais importantes antes de limpar
        for item in self.short_term.values():
            if item.importance >= 4:
                item.memory_type = "long_term"
                self.long_term[item.id] = item
        self._save_long_term()
        self.short_term = {}

    def get_context(self, query: str, max_items: int = 5) -> str:
        """Retorna contexto relevante para adicionar a prompts."""
        items = self.search(query, limit=max_items)
        if not items:
            return ""

        context_parts = ["Contexto relevante de conversas anteriores:"]
        for item in items:
            context_parts.append(f"- {item.content}")
        return "\n".join(context_parts)

    def get_stats(self) -> Dict[str, int]:
        """Retorna estatísticas da memória."""
        return {
            "short_term_count": len(self.short_term),
            "long_term_count": len(self.long_term),
            "total": len(self.short_term) + len(self.long_term)
        }

    def get_all_long_term(self, limit: int = 100) -> List[MemoryItem]:
        """Retorna todas as memórias de longo prazo."""
        items = sorted(
            self.long_term.values(),
            key=lambda x: x.last_accessed,
            reverse=True
        )
        return items[:limit]


class ShortTermMemory:
    """Memória de curto prazo (sessão atual)."""

    def __init__(self):
        self.conversation_history: List[Dict] = []
        self.current_context: Dict = {}
        self.session_start = datetime.now()

    def add_turn(self, role: str, content: str, action: str = ""):
        """Adiciona um turno à conversa."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "action": action,
            "timestamp": datetime.now().isoformat()
        })

    def get_recent(self, turns: int = 10) -> List[Dict]:
        """Retorna os últimos N turnos."""
        return self.conversation_history[-turns:]

    def get_conversation_text(self, turns: int = 10) -> str:
        """Retorna a conversa como texto."""
        recent = self.get_recent(turns)
        if not recent:
            return ""

        parts = []
        for turn in recent:
            role = "Usuário" if turn["role"] == "user" else "Jarvis"
            parts.append(f"{role}: {turn['content']}")
        return "\n".join(parts)

    def clear(self):
        """Limpa o histórico."""
        self.conversation_history = []
        self.current_context = {}


class LongTermMemory:
    """Memória de longo prazo (persistente)."""

    def __init__(self):
        self.memory_manager = MemoryManager()
        self.important_facts_file = LONG_TERM_DIR / "important_facts.json"
        self.important_facts: Dict[str, Any] = {}
        self._load_facts()

    def _load_facts(self):
        """Carrega fatos importantes."""
        if self.important_facts_file.exists():
            try:
                self.important_facts = json.loads(self.important_facts_file.read_text())
            except json.JSONDecodeError:
                self.important_facts = {}

    def _save_facts(self):
        """Salva fatos importantes."""
        self.important_facts_file.write_text(
            json.dumps(self.important_facts, indent=2, ensure_ascii=False)
        )

    def remember(self, key: str, value: Any):
        """Armazena um fato importante."""
        self.important_facts[key] = {
            "value": value,
            "updated_at": datetime.now().isoformat()
        }
        self._save_facts()

    def recall(self, key: str, default: Any = None) -> Any:
        """Recupera um fato importante."""
        fact = self.important_facts.get(key)
        if fact:
            return fact.get("value", default)
        return default

    def forget(self, key: str) -> bool:
        """Esquece um fato."""
        if key in self.important_facts:
            del self.important_facts[key]
            self._save_facts()
            return True
        return False

    def get_all_facts(self) -> Dict[str, Any]:
        """Retorna todos os fatos."""
        return {k: v["value"] for k, v in self.important_facts.items()}


# Instâncias globais
memory_manager = MemoryManager()
short_term_memory = ShortTermMemory()
long_term_memory = LongTermMemory()