"""
Analyzer ML System - Aprendizado de Maquina para Analise de Projetos
Sistema de pontuacao inteligente, confidence score e aprendizado continuo
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter
from data.core_database import get_jarvis_db


class AnalyzerML:
    """
    Sistema de ML para analise de projetos.
    Aprende com feedback do usuario para melhorar precisao.
    """

    def __init__(self):
        self.db = get_jarvis_db()
        self.exploration_rate = 0.1  # 10% chance de explorar novas estrategias
        self.min_confidence = 0.3
        self.max_confidence = 0.95

        # Load learned weights
        self.weights = self._load_weights()

    def _load_weights(self) -> Dict:
        """Carrega pesos aprendidos do banco."""
        weights = {
            # Tipo de problema -> peso base
            "type_weights": {
                "syntax": 1.0,
                "import": 0.9,
                "security": 1.0,
                "performance": 0.7,
                "architecture": 0.5,
                "unused": 0.3,
                "duplicate": 0.4,
                "style": 0.2
            },
            # Severidade -> peso
            "severity_weights": {
                "critical": 1.0,
                "high": 0.75,
                "medium": 0.5,
                "low": 0.25,
                "info": 0.1
            },
            # Metricas aprendidas
            "issue_type_accuracy": {},  # type -> accuracy
            "rule_accuracy": {},  # rule_id -> accuracy
            "suggestion_acceptance_rate": {},  # type -> rate
            "false_positive_rate": {},  # type -> rate
        }

        # Carregar do banco se disponivel
        if self.db:
            try:
                pref = self.db.get_preference("analyzer_ml_weights")
                if pref:
                    saved = json.loads(pref)
                    weights.update(saved)
            except:
                pass

        return weights

    def _save_weights(self):
        """Salva pesos aprendidos no banco."""
        if not self.db:
            return

        try:
            # Salvar apenas metricas learned
            learned = {
                "issue_type_accuracy": self.weights.get("issue_type_accuracy", {}),
                "rule_accuracy": self.weights.get("rule_accuracy", {}),
                "suggestion_acceptance_rate": self.weights.get("suggestion_acceptance_rate", {}),
                "false_positive_rate": self.weights.get("false_positive_rate", {}),
            }
            self.db.set_preference("analyzer_ml_weights", json.dumps(learned))
        except Exception as e:
            print(f"[ANALYZER ML] Erro ao salvar pesos: {e}")

    def record_analysis(self, project_name: str, issues: List[Dict],
                      suggestions_accepted: int, suggestions_rejected: int):
        """Registra uma analise para aprendizado."""
        if not self.db:
            return

        try:
            # Calcular metricas
            total_suggestions = suggestions_accepted + suggestions_rejected
            if total_suggestions > 0:
                acceptance_rate = suggestions_accepted / total_suggestions

                # Atualizar taxa de aceitacao por tipo
                for issue in issues:
                    issue_type = issue.get('type', 'unknown')
                    if issue_type not in self.weights["suggestion_acceptance_rate"]:
                        self.weights["suggestion_acceptance_rate"][issue_type] = []

                    self.weights["suggestion_acceptance_rate"][issue_type].append(
                        1 if suggestions_accepted > 0 else 0
                    )

                    # Manter apenas ultimos 100
                    if len(self.weights["suggestion_acceptance_rate"][issue_type]) > 100:
                        self.weights["suggestion_acceptance_rate"][issue_type] = \
                            self.weights["suggestion_acceptance_rate"][issue_type][-100:]

            self._save_weights()

        except Exception as e:
            print(f"[ANALYZER ML] Erro ao registrar analise: {e}")

    def record_feedback(self, issue_type: str, rule_id: str,
                       accepted: bool, actually_fixed: bool = None):
        """
        Registra feedback do usuario sobre uma analise.

        Recompensas:
        - Sugestao aceita + realmente resolveu = +2.0
        - Sugestao aceita = +1.0
        - Sugestao rejeitada = -0.5
        - Analise incorreta (false positive) = -1.0
        """
        reward = 0.0

        if actually_fixed:
            reward = 2.0  # Melhor caso
        elif accepted:
            reward = 1.0
        else:
            reward = -0.5

        # Atualizar accuracy do tipo
        if issue_type not in self.weights["issue_type_accuracy"]:
            self.weights["issue_type_accuracy"][issue_type] = []

        # Calcular nova accuracy
        current = self.weights["issue_type_accuracy"][issue_type]
        if accepted or actually_fixed:
            current.append(1)
        else:
            current.append(0)

        # Manter apenas ultimos 50
        if len(current) > 50:
            current = current[-50:]

        self.weights["issue_type_accuracy"][issue_type] = current

        # Atualizar accuracy da regra
        if rule_id:
            if rule_id not in self.weights["rule_accuracy"]:
                self.weights["rule_accuracy"][rule_id] = []

            if accepted:
                self.weights["rule_accuracy"][rule_id].append(1)
            else:
                self.weights["rule_accuracy"][rule_id].append(0)

            if len(self.weights["rule_accuracy"][rule_id]) > 50:
                self.weights["rule_accuracy"][rule_id] = \
                    self.weights["rule_accuracy"][rule_id][-50:]

        self._save_weights()

        return reward

    def get_acceptance_probability(self, issue_type: str) -> float:
        """Retorna probabilidade de aceitacao para um tipo de problema."""
        rates = self.weights.get("suggestion_acceptance_rate", {}).get(issue_type, [])
        if not rates:
            return 0.5  # Default

        return sum(rates) / len(rates)

    def get_type_accuracy(self, issue_type: str) -> float:
        """Retorna precisao historica para um tipo de problema."""
        accuracies = self.weights.get("issue_type_accuracy", {}).get(issue_type, [])
        if not accuracies:
            return 0.5

        return sum(accuracies) / len(accuracies)

    def get_rule_accuracy(self, rule_id: str) -> float:
        """Retorna precisao historica para uma regra."""
        accuracies = self.weights.get("rule_accuracy", {}).get(rule_id, [])
        if not accuracies:
            return 0.5

        return sum(accuracies) / len(accuracies)

    def calculate_confidence(self, issue_type: str, rule_id: str = None,
                           sample_size: int = 0) -> float:
        """
        Calcula confidence score (0.0 - 1.0) para uma analise.

        Fatores:
        - Precisao historica do tipo
        - Precisao da regra
        - Tamanho da amostra (mais analises = mais confianca)
        - Tempo desde a ultima analise
        """
        type_acc = self.get_type_accuracy(issue_type)

        if rule_id:
            rule_acc = self.get_rule_accuracy(rule_id)
            base_confidence = (type_acc * 0.7 + rule_acc * 0.3)
        else:
            base_confidence = type_acc

        # Ajuste por sample size (mais samples = mais confianca, ate um limite)
        if sample_size > 0:
            sample_bonus = min(0.1, sample_size * 0.01)
            base_confidence = min(0.95, base_confidence + sample_bonus)

        # Garantir limites
        confidence = max(self.min_confidence, min(self.max_confidence, base_confidence))

        return round(confidence, 2)

    def should_explore(self) -> bool:
        """Decide se deve explorar novas estrategias ou explotar conhecidas."""
        import random
        return random.random() < self.exploration_rate

    def get_prioritized_suggestions(self, issues: List[Dict]) -> List[Dict]:
        """
        Retorna sugestoes priorizadas usando exploracao vs explotacao.

        Explotacao: priorizar sugestoes com alta taxa de sucesso historico
        Exploracao: ocasionalmente testar novas sugestoes
        """
        if not issues:
            return []

        scored_issues = []

        for issue in issues:
            issue_type = issue.get('type', 'unknown')
            rule_id = issue.get('rule_id', '')

            # Calcular score base
            acceptance_prob = self.get_acceptance_probability(issue_type)
            accuracy = self.get_type_accuracy(issue_type)

            if rule_id:
                rule_acc = self.get_rule_accuracy(rule_id)
                base_score = (acceptance_prob * 0.4 + accuracy * 0.4 + rule_acc * 0.2)
            else:
                base_score = acceptance_prob * 0.6 + accuracy * 0.4

            # Aplicar exploracao se necessario
            if self.should_explore():
                # Adicionar ruido para explorar
                import random
                base_score += random.uniform(-0.2, 0.2)

            # Severidade tambem pesa
            severity_weights = {"critical": 1.5, "high": 1.2, "medium": 1.0, "low": 0.8, "info": 0.5}
            severity = issue.get('severity', 'medium')
            severity_bonus = severity_weights.get(severity, 1.0)

            final_score = base_score * severity_bonus

            scored_issues.append({
                **issue,
                'ml_score': round(final_score, 3),
                'confidence': self.calculate_confidence(issue_type, rule_id)
            })

        # Ordenar por score
        scored_issues.sort(key=lambda x: x['ml_score'], reverse=True)

        return scored_issues

    def get_strategy_ranking(self) -> List[Dict]:
        """Retorna ranking de estrategias de analise."""
        strategies = []

        for issue_type, rates in self.weights.get("suggestion_acceptance_rate", {}).items():
            if not rates:
                continue

            acceptance_rate = sum(rates) / len(rates)
            accuracy = self.get_type_accuracy(issue_type)

            # Score composto
            score = acceptance_rate * 0.5 + accuracy * 0.3 + (len(rates) / 100) * 0.2

            strategies.append({
                "type": issue_type,
                "acceptance_rate": round(acceptance_rate, 2),
                "accuracy": round(accuracy, 2),
                "sample_size": len(rates),
                "composite_score": round(score, 3)
            })

        # Ordenar por score composto
        strategies.sort(key=lambda x: x['composite_score'], reverse=True)

        return strategies

    def get_false_positive_rate(self, issue_type: str) -> float:
        """Retorna taxa de falsos positivos para um tipo."""
        accuracies = self.weights.get("issue_type_accuracy", {}).get(issue_type, [])
        if not accuracies:
            return 0.3  # Default

        # Falsos positivos sao quando accuracy baixa
        return 1.0 - (sum(accuracies) / len(accuracies))

    def adjust_confidence_for_fp_rate(self, base_confidence: float,
                                      issue_type: str) -> float:
        """Ajusta confianca baseado na taxa de falsos positivos."""
        fp_rate = self.get_false_positive_rate(issue_type)

        # Se alta taxa de FP, reduzir confianca
        if fp_rate > 0.5:
            return base_confidence * 0.7
        elif fp_rate > 0.3:
            return base_confidence * 0.9

        return base_confidence

    def get_learning_report(self) -> str:
        """Gera relatorio de aprendizado do sistema ML."""
        strategies = self.get_strategy_ranking()

        lines = [
            "🧠 ANALYZER ML - RELATORIO DE APRENDIZADO",
            "=" * 50,
            "",
            "📊 Ranking de Estrategias:",
            ""
        ]

        if not strategies:
            lines.append("  Nenhuma estrategia aprendida ainda.")
            lines.append("  Use o analyzer para comecar a aprender.")
        else:
            for i, s in enumerate(strategies[:10], 1):
                lines.append(
                    f"  {i}. {s['type']}: "
                    f"aceite={s['acceptance_rate']:.0%} "
                    f"precisao={s['accuracy']:.0%} "
                    f"score={s['composite_score']:.2f}"
                )

        lines.append("")
        lines.append("📈 Metricas Globais:")

        total_samples = sum(s['sample_size'] for s in strategies)
        avg_accuracy = sum(s['accuracy'] * s['sample_size'] for s in strategies) / max(total_samples, 1)

        lines.append(f"  Total de amostras: {total_samples}")
        lines.append(f"  Acuracia media: {avg_accuracy:.0%}")
        lines.append(f"  Taxa de exploracao: {self.exploration_rate:.0%}")

        return "\n".join(lines)

    def decay_weights(self, factor: float = 0.95):
        """Aplica decaimento aos pesos para privilegiar aprendizados recentes."""
        for issue_type in self.weights.get("issue_type_accuracy", {}):
            acc = self.weights["issue_type_accuracy"][issue_type]
            if len(acc) > 10:
                # Aplicar decaimento apenas aos mais antigos
                decay_amount = int(len(acc) * (1 - factor))
                if decay_amount > 0:
                    self.weights["issue_type_accuracy"][issue_type] = acc[decay_amount:]

        self._save_weights()


# Global instance
_ml = None


def get_analyzer_ml() -> AnalyzerML:
    """Retorna instancia global do ML."""
    global _ml
    if _ml is None:
        _ml = AnalyzerML()
    return _ml


def record_analysis(project_name: str, issues: List[Dict],
                  accepted: int, rejected: int):
    """Registra analise para aprendizado."""
    return get_analyzer_ml().record_analysis(project_name, issues, accepted, rejected)


def record_feedback(issue_type: str, rule_id: str, accepted: bool,
                   actually_fixed: bool = None) -> float:
    """Registra feedback e retorna recompensa."""
    return get_analyzer_ml().record_feedback(issue_type, rule_id, accepted, actually_fixed)


def get_prioritized_issues(issues: List[Dict]) -> List[Dict]:
    """Retorna issues priorizados por ML."""
    return get_analyzer_ml().get_prioritized_suggestions(issues)


def get_confidence(issue_type: str, rule_id: str = None) -> float:
    """Retorna confianca para um tipo de problema."""
    return get_analyzer_ml().calculate_confidence(issue_type, rule_id)


def get_learning_report() -> str:
    """Retorna relatorio de aprendizado."""
    return get_analyzer_ml().get_learning_report()