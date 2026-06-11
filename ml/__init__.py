"""
Jarvis MiniMax - Módulo de Machine Learning
Funcionalidades:
- Predição de comandos
- Análise de padrões de uso
- Treinamento ativo com feedback
- Sugestões de automação
"""

from .command_predictor import CommandPredictor
from .usage_analytics import UsageAnalytics
from .trainer import MLTrainer, get_trainer, train_model, get_training_stats

__all__ = ["CommandPredictor", "UsageAnalytics", "MLTrainer", "get_trainer", "train_model", "get_training_stats"]