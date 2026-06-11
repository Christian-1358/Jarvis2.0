"""
Análise de uso - Estatísticas e insights de uso do Jarvis
"""

import json
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from config.settings import DATA_DIR


class UsageAnalytics:
    """Coleta e analisa estatísticas de uso do Jarvis."""

    def __init__(self):
        self.stats_file = DATA_DIR / "usage_stats.json"
        self.daily_stats = {}
        self._load_stats()

    def _load_stats(self):
        """Carrega estatísticas salvas."""
        if self.stats_file.exists():
            try:
                self.daily_stats = json.loads(self.stats_file.read_text())
            except Exception:
                self.daily_stats = {}

    def _save_stats(self):
        """Salva estatísticas."""
        try:
            self.stats_file.parent.mkdir(parents=True, exist_ok=True)
            self.stats_file.write_text(json.dumps(self.daily_stats, indent=2))
        except Exception:
            pass

    def record_action(self, action: str):
        """Registra uma ação executada."""
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.daily_stats:
            self.daily_stats[today] = {"actions": [], "hourly": {}}

        self.daily_stats[today]["actions"].append(action)

        hour = datetime.now().hour
        if hour not in self.daily_stats[today]["hourly"]:
            self.daily_stats[today]["hourly"][hour] = 0
        self.daily_stats[today]["hourly"][hour] += 1

        self._save_stats()

    def get_summary(self) -> dict:
        """Retorna resumo de uso."""
        if not self.daily_stats:
            return {
                "total_actions": 0,
                "days_active": 0,
                "top_actions": [],
                "peak_hour": None
            }

        all_actions = []
        hourly_counts = defaultdict(int)

        for date, data in self.daily_stats.items():
            all_actions.extend(data.get("actions", []))
            for hour, count in data.get("hourly", {}).items():
                hourly_counts[hour] += count

        action_counts = Counter(all_actions)
        peak_hour = max(hourly_counts.keys(), key=lambda h: hourly_counts[h]) if hourly_counts else None

        return {
            "total_actions": len(all_actions),
            "days_active": len(self.daily_stats),
            "top_actions": action_counts.most_common(5),
            "peak_hour": peak_hour,
            "avg_daily": len(all_actions) / max(len(self.daily_stats), 1)
        }

    def get_weekly_report(self) -> str:
        """Gera relatório semanal."""
        summary = self.get_summary()

        if summary["total_actions"] == 0:
            return "Sem dados de uso ainda. Use o Jarvis mais para ver estatísticas!"

        lines = [
            "📊 Relatório Semanal do Jarvis",
            "=" * 30,
            f"Total de ações: {summary['total_actions']}",
            f"Dias ativos: {summary['days_active']}",
            f"Média diária: {summary['avg_daily']:.1f} ações",
            "",
            "🔥 Top 5 ações mais usadas:"
        ]

        for i, (action, count) in enumerate(summary["top_actions"], 1):
            lines.append(f"  {i}. {action}: {count}x")

        if summary["peak_hour"] is not None:
            peak = int(summary["peak_hour"])
            hour_str = f"{peak:02d}:00"
            lines.append(f"\n⏰ Horário de maior atividade: {hour_str}")

        return "\n".join(lines)

    def get_all_stats(self) -> dict:
        """Retorna todas as estatísticas."""
        return {
            "summary": self.get_summary(),
            "daily_stats": self.daily_stats
        }


# Instância global
_analytics = None


def get_analytics() -> UsageAnalytics:
    global _analytics
    if _analytics is None:
        _analytics = UsageAnalytics()
    return _analytics


def record_action(action: str):
    get_analytics().record_action(action)


def get_summary() -> dict:
    return get_analytics().get_summary()


def get_weekly_report() -> str:
    return get_analytics().get_weekly_report()