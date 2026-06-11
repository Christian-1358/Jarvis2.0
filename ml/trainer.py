"""
Treinador de ML - Sistema de aprendizado ativo
O Jarvis aprende com feedback do usuário para melhorar predições
"""

import json
from pathlib import Path
from collections import Counter
from datetime import datetime
from config.settings import DATA_DIR


class MLTrainer:
    """Sistema de treinamento ativo do Jarvis."""

    def __init__(self):
        self.feedback_file = DATA_DIR / "ml_feedback.json"
        self.model_file = DATA_DIR / "ml_model.json"
        self.feedback_data = []
        self.training_data = []
        self._load_data()

    def _load_data(self):
        """Carrega dados de feedback e modelo."""
        if self.feedback_file.exists():
            try:
                self.feedback_data = json.loads(self.feedback_file.read_text())
            except Exception:
                self.feedback_data = []

        if self.model_file.exists():
            try:
                model = json.loads(self.model_file.read_text())
                self.training_data = model.get("training_data", [])
            except Exception:
                self.training_data = []

    def _save_data(self):
        """Salva dados de feedback e modelo."""
        try:
            self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
            self.feedback_file.write_text(json.dumps(self.feedback_data, indent=2))

            model = {
                "training_data": self.training_data[-500:],  # Keep last 500 training examples
                "updated": datetime.now().isoformat()
            }
            self.model_file.write_text(json.dumps(model, indent=2))
        except Exception:
            pass

    def add_feedback(self, command: str, predicted_action: str, correct_action: str = None, rating: int = 0):
        """
        Adiciona feedback do usuário.
        rating: -1 (wrong), 0 (neutral), 1 (correct)
        """
        feedback = {
            "command": command.lower().strip(),
            "predicted_action": predicted_action,
            "correct_action": correct_action or predicted_action,
            "rating": rating,
            "timestamp": datetime.now().isoformat()
        }
        self.feedback_data.append(feedback)

        # Se foi correção, adiciona aos dados de treinamento
        if correct_action and correct_action != predicted_action:
            self.training_data.append({
                "input": command.lower().strip(),
                "output": correct_action,
                "type": "correction"
            })
        elif rating == 1:
            self.training_data.append({
                "input": command.lower().strip(),
                "output": predicted_action,
                "type": "confirmed"
            })

        self._save_data()

    def train(self) -> dict:
        """
        Executa treinamento no modelo.
        Retorna métricas de treinamento.
        """
        if len(self.training_data) < 5:
            return {
                "status": "insufficient_data",
                "samples": len(self.training_data),
                "message": "Dados insuficientes para treinamento. Continue usando e dando feedback!"
            }

        # Análise simples baseada em frequência
        action_patterns = {}

        for item in self.training_data:
            words = item["input"].split()
            # Usar bigramas para padrões
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i+1]}"
                if bigram not in action_patterns:
                    action_patterns[bigram] = Counter()
                action_patterns[bigram][item["output"]] += 1

        # Calcular accuracy do modelo
        correct = 0
        total = 0
        for item in self.training_data[-50:]:  # Test on recent data
            words = item["input"].split()
            predicted = None
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i+1]}"
                if bigram in action_patterns:
                    predicted = action_patterns[bigram].most_common(1)[0][0]
                    break

            if predicted == item["output"]:
                correct += 1
            total += 1

        accuracy = (correct / total * 100) if total > 0 else 0

        return {
            "status": "trained",
            "samples": len(self.training_data),
            "accuracy": accuracy,
            "patterns_learned": len(action_patterns),
            "message": f"Modelo treinado com {len(self.training_data)} amostras. Accuracy: {accuracy:.1f}%"
        }

    def predict_with_confidence(self, command: str) -> list:
        """
        Prediz ação com confiança baseada no modelo treinado.
        Retorna lista de (ação, confiança).
        """
        if not self.training_data:
            return []

        words = command.lower().split()
        action_scores = Counter()

        # Buscar padrões aprendidos
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            for item in self.training_data:
                item_words = item["input"].split()
                for j in range(len(item_words) - 1):
                    if f"{item_words[j]} {item_words[j+1]}" == bigram:
                        action_scores[item["output"]] += 1

        if not action_scores:
            return []

        total = sum(action_scores.values())
        predictions = []
        for action, score in action_scores.most_common(5):
            confidence = score / total
            predictions.append((action, confidence))

        return predictions

    def get_training_stats(self) -> dict:
        """Retorna estatísticas de treinamento."""
        return {
            "total_feedback": len(self.feedback_data),
            "training_samples": len(self.training_data),
            "corrections": sum(1 for f in self.feedback_data if f.get("correct_action") != f.get("predicted_action")),
            "confirmations": sum(1 for f in self.feedback_data if f.get("rating") == 1),
            "last_update": self.training_data[-1]["input"] if self.training_data else None
        }


# Instância global
_trainer = None


def get_trainer() -> MLTrainer:
    global _trainer
    if _trainer is None:
        _trainer = MLTrainer()
    return _trainer


def add_feedback(command: str, predicted: str, correct: str = None, rating: int = 0):
    return get_trainer().add_feedback(command, predicted, correct, rating)


def train_model() -> dict:
    return get_trainer().train()


def predict(command: str) -> list:
    return get_trainer().predict_with_confidence(command)


def get_training_stats() -> dict:
    return get_trainer().get_training_stats()