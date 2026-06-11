"""
Preditor de comandos - Usa histórico para prever próximos comandos
"""

import json
from pathlib import Path
from collections import Counter
from datetime import datetime, timedelta
from config.settings import DATA_DIR


class CommandPredictor:
    """Prediz próximos comandos baseado em padrões de uso."""

    def __init__(self):
        self.history_file = DATA_DIR / "command_history.json"
        self.commands = []
        self.sequence_length = 3  # número de comandos anteriores para considerar
        self._load_history()

    def _load_history(self):
        """Carrega histórico de comandos."""
        if self.history_file.exists():
            try:
                data = json.loads(self.history_file.read_text())
                self.commands = data.get("commands", [])
            except Exception:
                self.commands = []

    def _save_history(self):
        """Salva histórico de comandos."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            self.history_file.write_text(json.dumps({"commands": self.commands[-1000:]}, indent=2))
        except Exception:
            pass

    def add_command(self, command: str, action: str):
        """Adiciona comando ao histórico."""
        self.commands.append({
            "command": command.lower().strip(),
            "action": action,
            "timestamp": datetime.now().isoformat()
        })
        self._save_history()

    def predict_next(self, current_command: str = None) -> list:
        """
        Prediz próximos comandos prováveis.
        Retorna lista de tuplas (comando, confiança).
        """
        if len(self.commands) < 5:
            return []

        # Análise de frequência simples
        recent = self.commands[-50:]
        action_counts = Counter(c["action"] for c in recent)

        predictions = []
        for action, count in action_counts.most_common(5):
            confidence = count / len(recent)
            predictions.append((action, confidence))

        return predictions

    def get_routine_suggestions(self) -> list:
        """Detecta rotinas baseadas em padrões temporais."""
        if len(self.commands) < 20:
            return []

        # Agrupar por hora do dia
        hourly_actions = {}
        for entry in self.commands:
            try:
                dt = datetime.fromisoformat(entry["timestamp"])
                hour = dt.hour
                if hour not in hourly_actions:
                    hourly_actions[hour] = []
                hourly_actions[hour].append(entry["action"])
            except Exception:
                continue

        suggestions = []
        for hour, actions in hourly_actions.items():
            if len(actions) >= 3:
                counter = Counter(actions)
                most_common = counter.most_common(1)[0]
                suggestions.append({
                    "hour": hour,
                    "action": most_common[0],
                    "confidence": most_common[1] / len(actions)
                })

        return suggestions

    def get_stats(self) -> dict:
        """Retorna estatísticas de uso."""
        if not self.commands:
            return {"total_commands": 0, "unique_actions": 0}

        actions = [c["action"] for c in self.commands]
        action_counts = Counter(actions)

        return {
            "total_commands": len(self.commands),
            "unique_actions": len(action_counts),
            "top_actions": action_counts.most_common(5),
            "last_command": self.commands[-1] if self.commands else None
        }


# Instância global
_predictor = None


def get_predictor() -> CommandPredictor:
    global _predictor
    if _predictor is None:
        _predictor = CommandPredictor()
    return _predictor


def predict_next(command: str = None) -> list:
    return get_predictor().predict_next(command)


def add_command(command: str, action: str):
    get_predictor().add_command(command, action)


def get_stats() -> dict:
    return get_predictor().get_stats()