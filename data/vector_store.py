"""
Camada de dados - Vector Store para embeddings e busca semântica
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import numpy as np

BASE_DIR = Path(__file__).parent.parent
EMBEDDINGS_DIR = BASE_DIR / "dados" / "embeddings"

EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class EmbeddingRecord:
    """Registro de embedding."""
    id: str
    text: str
    embedding: List[float]
    metadata: Dict
    created_at: str


class VectorStore:
    """
    Vector store simples baseado em cossine similarity.
    Usa numpy para cálculos de similaridade.
    """

    def __init__(self, collection: str = "default"):
        self.collection = collection
        self.embeddings_file = EMBEDDINGS_DIR / f"{collection}.json"
        self.embeddings: Dict[str, EmbeddingRecord] = {}
        self._load()

    def _load(self):
        """Carrega os embeddings do disco."""
        if self.embeddings_file.exists():
            try:
                data = json.loads(self.embeddings_file.read_text())
                self.embeddings = {
                    k: EmbeddingRecord(**v) for k, v in data.items()
                }
            except (json.JSONDecodeError, TypeError):
                self.embeddings = {}

    def _save(self):
        """Salva os embeddings no disco."""
        data = {k: asdict(v) for k, v in self.embeddings.items()}
        self.embeddings_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def _generate_id(self, text: str) -> str:
        """Gera um ID único baseado no hash do texto."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calcula similaridade por cosseno."""
        a = np.array(a)
        b = np.array(b)
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot_product / (norm_a * norm_b))

    def _simple_embed(self, text: str) -> List[float]:
        """
        Gera um embedding simples baseado em palavras.
        Fallback quando sentence-transformers não está disponível.
        """
        words = text.lower().split()
        vocab_size = 100
        vector = np.zeros(vocab_size)
        for i, word in enumerate(words[:vocab_size]):
            vector[i % vocab_size] += hash(word) % 100 / 100.0
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector.tolist()

    def add(self, text: str, metadata: Optional[Dict] = None) -> str:
        """Adiciona um texto ao vector store."""
        record_id = self._generate_id(text)
        if record_id in self.embeddings:
            return record_id

        embedding = self._simple_embed(text)
        self.embeddings[record_id] = EmbeddingRecord(
            id=record_id,
            text=text,
            embedding=embedding,
            metadata=metadata or {},
            created_at=datetime.now().isoformat()
        )
        self._save()
        return record_id

    def search(self, query: str, top_k: int = 5, threshold: float = 0.0) -> List[Tuple[str, float, Dict]]:
        """
        Busca os k textos mais similares.
        Retorna lista de tuplas (id, score, metadata).
        """
        if not self.embeddings:
            return []

        query_embedding = self._simple_embed(query)
        results = []

        for record_id, record in self.embeddings.items():
            score = self._cosine_similarity(query_embedding, record.embedding)
            if score >= threshold:
                results.append((record_id, score, record.metadata))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def get(self, record_id: str) -> Optional[EmbeddingRecord]:
        """Retorna um registro pelo ID."""
        return self.embeddings.get(record_id)

    def delete(self, record_id: str) -> bool:
        """Remove um registro."""
        if record_id in self.embeddings:
            del self.embeddings[record_id]
            self._save()
            return True
        return False

    def count(self) -> int:
        """Conta quantos registros existem."""
        return len(self.embeddings)

    def clear(self):
        """Limpa todos os registros."""
        self.embeddings = {}
        self._save()


class ConversationStore(VectorStore):
    """Store especializado para conversas."""

    def __init__(self):
        super().__init__("conversations")

    def add_exchange(self, user_input: str, assistant_response: str,
                     action: str = "", success: bool = True):
        """Adiciona um intercambio de conversa."""
        exchange_text = f"User: {user_input}\nAssistant: {assistant_response}"
        metadata = {
            "type": "exchange",
            "action": action,
            "success": success,
            "user_input": user_input,
            "assistant_response": assistant_response
        }
        return self.add(exchange_text, metadata)

    def search_conversation(self, query: str, top_k: int = 5) -> List[Dict]:
        """Busca em conversas passadas."""
        results = self.search(query, top_k)
        return [
            {
                "id": record_id,
                "score": score,
                **metadata
            }
            for record_id, score, metadata in results
        ]


class CommandStore(VectorStore):
    """Store especializado para comandos."""

    def __init__(self):
        super().__init__("commands")

    def add_command(self, command: str, action: str, target: str = "",
                    result: str = "", success: bool = True):
        """Adiciona um comando executado."""
        metadata = {
            "type": "command",
            "action": action,
            "target": target,
            "result": result[:200] if result else "",
            "success": success
        }
        return self.add(command, metadata)

    def search_commands(self, query: str, top_k: int = 5) -> List[Dict]:
        """Busca comandos similares."""
        results = self.search(query, top_k)
        return [
            {
                "id": record_id,
                "score": score,
                **metadata
            }
            for record_id, score, metadata in results
        ]

    def get_recent_by_action(self, action: str, limit: int = 10) -> List[Dict]:
        """Retorna comandos recentes de uma ação específica."""
        results = []
        for record_id, record in self.embeddings.items():
            if record.metadata.get("action") == action:
                results.append({
                    "id": record_id,
                    "text": record.text,
                    **record.metadata
                })
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return results[:limit]


class KnowledgeStore(VectorStore):
    """Store para base de conhecimento pessoal."""

    def __init__(self):
        super().__init__("knowledge")

    def add_knowledge(self, content: str, category: str = "",
                       tags: Optional[List[str]] = None):
        """Adiciona conhecimento."""
        metadata = {
            "type": "knowledge",
            "category": category,
            "tags": tags or []
        }
        return self.add(content, metadata)

    def search_knowledge(self, query: str, category: Optional[str] = None,
                         top_k: int = 5) -> List[Dict]:
        """Busca conhecimento."""
        results = self.search(query, top_k)
        filtered = []
        for record_id, score, metadata in results:
            if category and metadata.get("category") != category:
                continue
            filtered.append({
                "id": record_id,
                "score": score,
                "text": self.embeddings[record_id].text,
                **metadata
            })
        return filtered