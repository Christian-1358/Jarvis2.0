"""
Jarvis RL System - Aprendizado por Reforço com Banco de Dados SQL
Sistema de pontuação e adaptação contínua baseado em feedback do usuário
Persistência em SQLite para escalabilidade e robustez
"""

from datetime import datetime
from data.rl_database import get_database


class RLJarvis:
    """Sistema de Aprendizado por Reforço do Jarvis com persistência SQL."""

    def __init__(self):
        self.db = get_database()
        self.weights = {
            "correct": 1.0,
            "incorrect": -0.5,
            "neutral": 0.0
        }

    def reward(self, action: str, reward_type: str = "correct", context: str = "",
              command: str = "", result: str = "") -> dict:
        """
        Registra uma recompensa para uma ação.
        reward_type: "correct", "incorrect", "neutral"

        Returns:
            dict com action, reward, total_score, times_used
        """
        reward_value = self.weights.get(reward_type, 0.0)
        success = reward_value >= 0

        # Log do feedback individual
        self.db.log_feedback(
            action=action,
            reward_type=reward_type,
            reward_value=reward_value,
            context=context,
            command=command,
            result=result,
            success=success
        )

        # Atualiza estatísticas da ação
        self.db.update_action_stats(action, reward_value, success)

        # Atualiza score por contexto
        if context:
            self.db.update_context_score(context, action, reward_value, success)

        # Obtém estatísticas atualizadas
        stats = self.db.get_action_stats(action)

        return {
            "action": action,
            "reward": reward_value,
            "total_score": round(stats["total_score"], 2) if stats else round(reward_value, 2),
            "times_used": stats["use_count"] if stats else 1
        }

    def get_best_action(self, context: str = "", available_actions: list = None) -> dict:
        """
        Retorna a melhor ação baseada no histórico de recompensas.
        Se houver contexto, considera padrões de preferência.
        """
        if context:
            result = self.db.get_best_action_for_context(context, available_actions)
            if result["action"]:
                return result

        # Fallback para global
        top = self.db.get_top_actions(limit=5)
        if not top:
            return {"action": None, "confidence": 0, "source": "no_data"}

        best = top[0]
        confidence = min(0.95, 0.5 + (best["score"] / 20))

        return {
            "action": best["action"],
            "score": best["score"],
            "confidence": round(confidence, 2),
            "source": "global"
        }

    def get_top_actions(self, limit: int = 5) -> list:
        """Retorna as ações com melhor pontuação."""
        return self.db.get_top_actions(limit)

    def get_action_stats(self, action: str) -> dict:
        """Retorna estatísticas detalhadas de uma ação."""
        stats = self.db.get_action_stats(action)
        if not stats:
            return {
                "action": action,
                "total_score": 0,
                "times_used": 0,
                "avg_score": 0,
                "trend": "neutral"
            }

        trend = "up" if stats["total_score"] > 0 else "down" if stats["total_score"] < 0 else "neutral"

        return {
            "action": action,
            "total_score": round(stats["total_score"], 2),
            "times_used": stats["use_count"],
            "avg_score": round(stats["avg_score"], 2),
            "success_rate": round(stats["success_rate"] * 100, 1),
            "trend": trend
        }

    def get_context_actions(self, context: str, limit: int = 5) -> list:
        """Retorna as melhores ações para um contexto específico."""
        return self.db.get_context_actions(context, limit)

    def get_recent_trends(self, days: int = 7) -> list:
        """Retorna tendências recentes de aprendizado."""
        return self.db.get_recent_trends(days)

    def decay_scores(self, factor: float = 0.95):
        """Aplica decaimento aos scores para privilegiar aprendizados recentes."""
        self.db.decay_scores(factor)

    def get_learning_report(self) -> str:
        """Gera relatório de aprendizado do sistema RL."""
        summary = self.db.get_learning_summary()
        top = self.get_top_actions(5)
        recent = self.get_recent_trends(3)

        lines = [
            "🧠 Sistema de Aprendizado por Reforço (SQL)",
            "=" * 45,
            f"Total de feedbacks: {summary['total_feedbacks']}",
            f"Ações aprendidas: {summary['unique_actions']}",
            f"Ações positivas: {summary['positive_actions']}",
            f"Ações negativas: {summary['negative_actions']}",
            "",
            "🏆 Top 5 ações mais recompensadas:",
        ]

        for i, item in enumerate(top, 1):
            trend = "📈" if item["score"] > 0 else "📉"
            success = f"{item.get('success_rate', 0):.0%}" if item.get('success_rate') else "N/A"
            lines.append(f"  {i}. {item['action']}: {item['score']:.1f} pts ({item['times']}x) {trend} (sucesso: {success})")

        if recent:
            lines.append("")
            lines.append("📊 Tendência recente (3 dias):")
            for r in recent[:5]:
                lines.append(f"  - {r['action']}: {r['count']}x, reward médio: {r['avg_reward']:.2f}")

        if summary['total_feedbacks'] < 5:
            lines.append("")
            lines.append("💡 Dica: Use 'rl_approve' para ensinar o Jarvis!")

        return "\n".join(lines)

    def get_detailed_stats(self, action: str = "") -> dict:
        """Retorna estatísticas detalhadas do sistema ou de uma ação."""
        if action:
            stats = self.get_action_stats(action)
            history = self.db.get_action_history(action, limit=20)

            # Calcular tendência (últimos 5 feedbacks)
            recent_rewards = [h["reward_value"] for h in history[:5]]
            trend = "stable"
            if len(recent_rewards) >= 3:
                first_half = sum(recent_rewards[:len(recent_rewards)//2])
                second_half = sum(recent_rewards[len(recent_rewards)//2:])
                if second_half > first_half:
                    trend = "improving"
                elif second_half < first_half:
                    trend = "declining"

            return {
                "stats": stats,
                "history": history,
                "trend": trend
            }

        return {
            "summary": self.db.get_learning_summary(),
            "top_actions": self.get_top_actions(10),
            "contexts": self.db.get_all_contexts()
        }

    def export_learning(self) -> dict:
        """Exporta todo o aprendizado para backup."""
        summary = self.db.get_learning_summary()
        top = self.db.get_top_actions(20)
        contexts = []
        for ctx in self.db.get_all_contexts():
            contexts.append({
                "context": ctx,
                "actions": self.db.get_context_actions(ctx, limit=10)
            })

        return {
            "exported_at": datetime.now().isoformat(),
            "summary": summary,
            "top_actions": top,
            "contexts": contexts
        }

    def import_learning(self, data: dict):
        """Importa aprendizado de backup (para futuras restores)."""
        # Implementação futura para restore de backups
        pass


# Instância global
_rl = None


def get_rl() -> RLJarvis:
    """Retorna a instância global do sistema RL."""
    global _rl
    if _rl is None:
        _rl = RLJarvis()
    return _rl


def reward_action(action: str, reward_type: str = "correct", context: str = ""):
    """Registra recompensa para uma ação."""
    return get_rl().reward(action, reward_type, context)


def get_best_action(context: str = "", available_actions: list = None):
    """Retorna melhor ação baseada em aprendizado."""
    return get_rl().get_best_action(context, available_actions)


def get_learning_report():
    """Retorna relatório de aprendizado."""
    return get_rl().get_learning_report()


def get_action_stats(action: str):
    """Retorna estatísticas de uma ação."""
    return get_rl().get_action_stats(action)