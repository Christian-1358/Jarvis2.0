"""
Análise de uso - Estatísticas e insights de uso do Jarvis
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from data.core_database import get_jarvis_db


class UsageAnalytics:
    """Coleta e analisa estatísticas de uso do Jarvis."""

    def __init__(self):
        self.db = get_jarvis_db()
        self.daily_stats = {}
        self._load_stats()

    def _load_stats(self):
        """Carrega estatísticas do banco."""
        if not self.db:
            return
        try:
            with self.db._conn() as conn:
                rows = conn.execute(
                    "SELECT date, hour, action, count FROM usage_stats ORDER BY date DESC"
                ).fetchall()
                for row in rows:
                    date, hour, action, count = row
                    if date not in self.daily_stats:
                        self.daily_stats[date] = {"actions": [], "hourly": {}}
                    self.daily_stats[date]["actions"].extend([action] * count)
                    if hour not in self.daily_stats[date]["hourly"]:
                        self.daily_stats[date]["hourly"][hour] = 0
                    self.daily_stats[date]["hourly"][hour] += count
        except Exception:
            self.daily_stats = {}

    def record_action(self, action: str):
        """Registra uma ação executada."""
        if not self.db:
            return
        today = datetime.now().strftime("%Y-%m-%d")
        hour = datetime.now().hour

        try:
            with self.db._conn() as conn:
                conn.execute("""
                    INSERT INTO usage_stats (date, hour, action, count, success_count)
                    VALUES (?, ?, ?,1, 1)
                    ON CONFLICT(date, hour, action) DO UPDATE SET
                        count = count + 1,
                        success_count = success_count + 1
                """, (today, hour, action))
        except Exception:
            pass

    def get_summary(self) -> dict:
        """Retorna resumo de uso."""
        if not self.db:
            return {
                "total_actions": 0,
                "days_active": 0,
                "top_actions": [],
                "peak_hour": None
            }

        try:
            with self.db._conn() as conn:
                rows = conn.execute("""
                    SELECT action, SUM(count) as total
                    FROM usage_stats
                    GROUP BY action
                    ORDER BY total DESC
                    LIMIT 5
                """).fetchall()
                top_actions = [(row[0], row[1]) for row in rows]

                total = conn.execute("SELECT SUM(count) FROM usage_stats").fetchone()[0] or 0
                days = conn.execute("SELECT COUNT(DISTINCT date) FROM usage_stats").fetchone()[0] or 0
                peak = conn.execute("""
                    SELECT hour FROM usage_stats GROUP BY hour ORDER BY SUM(count) DESC LIMIT 1
                """).fetchone()

                return {
                    "total_actions": total,
                    "days_active": days,
                    "top_actions": top_actions,
                    "peak_hour": peak[0] if peak else None,
                    "avg_daily": total / max(days, 1)
                }
        except Exception:
            return {
                "total_actions": 0,
                "days_active": 0,
                "top_actions": [],
                "peak_hour": None
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
            hour_str = f"{summary['peak_hour']:02d}:00"
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