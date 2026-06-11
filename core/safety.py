"""
Jarvis Safety System - Sistema de Confirmacao para Acoes Perigosas
Todas as acoes perigosas requerem confirmacao explicita do usuario
"""

from typing import Optional, Callable, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class DangerousAction:
    """Representa uma acao perigosa."""
    name: str
    description: str
    risk_level: str  # low, medium, high, critical
    confirmation_phrase: str
    timeout_seconds: int = 30


class SafetyManager:
    """Gerenciador de seguranca para acoes perigosas."""

    # Acoes perigosas predefinidas
    DANGEROUS_ACTIONS = {
        "delete_file": DangerousAction(
            name="delete_file",
            description="Apagar arquivos permanentemente",
            risk_level="high",
            confirmation_phrase="sim, apagar"
        ),
        "shutdown_pc": DangerousAction(
            name="shutdown_pc",
            description="Desligar o computador imediatamente",
            risk_level="critical",
            confirmation_phrase="sim, desligar"
        ),
        "restart_pc": DangerousAction(
            name="restart_pc",
            description="Reiniciar o computador",
            risk_level="high",
            confirmation_phrase="sim, reiniciar"
        ),
        "hibernate_pc": DangerousAction(
            name="hibernate_pc",
            description="Hibernar o computador",
            risk_level="medium",
            confirmation_phrase="sim, hibernar"
        ),
        "format_disk": DangerousAction(
            name="format_disk",
            description="Formatar disco (nao implementado)",
            risk_level="critical",
            confirmation_phrase="IMPOSSIBLE"
        ),
        "run_command": DangerousAction(
            name="run_command",
            description="Executar comandos no terminal",
            risk_level="high",
            confirmation_phrase="sim, executar"
        ),
        "drop_database": DangerousAction(
            name="drop_database",
            description="Apagar banco de dados",
            risk_level="critical",
            confirmation_phrase="IMPOSSIBLE"
        ),
    }

    def __init__(self):
        self._pending_confirmations: Dict = {}
        self._confirmation_history: list = []
        self._auto_approved_sessions: set = set()

    def is_dangerous(self, action: str) -> bool:
        """Verifica se uma acao e perigosa."""
        return action in self.DANGEROUS_ACTIONS

    def get_danger_info(self, action: str):
        """Retorna informacoes de perigo de uma acao."""
        return self.DANGEROUS_ACTIONS.get(action)

    def requires_confirmation(self, action: str) -> bool:
        """Verifica se uma acao requer confirmacao."""
        if action in self.DANGEROUS_ACTIONS:
            return self.DANGEROUS_ACTIONS[action].risk_level in ["high", "critical"]
        return False

    def request_confirmation(self, action: str, target: str = "", session_id: str = None) -> dict:
        """
        Solicita confirmacao para uma acao perigosa.
        Retorna dict com status e instrucao.
        """
        danger_info = self.get_danger_info(action)
        if not danger_info:
            return {"needs_confirmation": False}

        confirmation_id = f"{action}_{datetime.now().timestamp()}"

        self._pending_confirmations[confirmation_id] = {
            "action": action,
            "target": target,
            "session_id": session_id,
            "created_at": datetime.now(),
            "timeout": timedelta(seconds=danger_info.timeout_seconds)
        }

        risk_emoji = {
            "low": "⚠️",
            "medium": "🔶",
            "high": "🔴",
            "critical": "☠️"
        }

        return {
            "needs_confirmation": True,
            "confirmation_id": confirmation_id,
            "action": action,
            "description": danger_info.description,
            "risk_level": danger_info.risk_level,
            "risk_emoji": risk_emoji.get(danger_info.risk_level, "⚠️"),
            "confirmation_phrase": danger_info.confirmation_phrase,
            "target": target,
            "message": (
                f"{risk_emoji.get(danger_info.risk_level, '⚠️')} ACAO PERIGOSA: {action}\n"
                f"Descricao: {danger_info.description}\n"
                f"Alvo: {target or 'N/A'}\n"
                f"Risco: {danger_info.risk_level.upper()}\n\n"
                f"Para confirmar, digite: '{danger_info.confirmation_phrase}'\n"
                f"Ou aguarde {danger_info.timeout_seconds}s para cancelar automaticamente."
            )
        }

    def check_confirmation(self, confirmation_id: str, user_response: str) -> dict:
        """Verifica se a resposta do usuario confirma a acao."""
        if confirmation_id not in self._pending_confirmations:
            return {"confirmed": False, "reason": "Confirmacao nao encontrada ou expirada"}

        pending = self._pending_confirmations[confirmation_id]

        # Verificar timeout
        if datetime.now() - pending["created_at"] > pending["timeout"]:
            del self._pending_confirmations[confirmation_id]
            return {"confirmed": False, "reason": "Tempo de confirmacao expirado"}

        danger_info = self.get_danger_info(pending["action"])
        expected_phrase = danger_info.confirmation_phrase.lower() if danger_info else ""

        # Verificar resposta
        response_lower = user_response.lower().strip()

        if response_lower == expected_phrase or response_lower == "sim":
            # Confirmado
            del self._pending_confirmations[confirmation_id]
            self._confirmation_history.append({
                "action": pending["action"],
                "target": pending["target"],
                "confirmed_at": datetime.now(),
                "session_id": pending["session_id"]
            })
            return {"confirmed": True, "action": pending["action"]}

        return {"confirmed": False, "reason": "Confirmacao nao reconhecida"}

    def cancel_pending(self, confirmation_id: str):
        """Cancela uma confirmacao pendente."""
        if confirmation_id in self._pending_confirmations:
            del self._pending_confirmations[confirmation_id]

    def is_auto_approved(self, session_id: str) -> bool:
        """Verifica se uma sessao tem aprovacao automatica."""
        return session_id in self._auto_approved_sessions

    def add_auto_approved(self, session_id: str, duration_minutes: int = 30):
        """Adiciona uma sessao a lista de aprovacao automatica."""
        self._auto_approved_sessions.add(session_id)
        # Auto-remover apos duration
        import threading
        def remove():
            import time
            time.sleep(duration_minutes * 60)
            self._auto_approved_sessions.discard(session_id)
        threading.Thread(target=remove, daemon=True).start()

    def get_confirmation_history(self, limit: int = 50) -> list:
        """Retorna historico de confirmacoes."""
        return self._confirmation_history[-limit:]

    def get_pending_count(self) -> int:
        """Retorna numero de confirmacoes pendentes."""
        return len(self._pending_confirmations)


# Instancia global
_safety = None


def get_safety() -> SafetyManager:
    """Retorna instancia global do gerenciador de seguranca."""
    global _safety
    if _safety is None:
        _safety = SafetyManager()
    return _safety


def is_dangerous(action: str) -> bool:
    """Verifica se uma acao e perigosa."""
    return get_safety().is_dangerous(action)


def requires_confirmation(action: str) -> bool:
    """Verifica se uma acao requer confirmacao."""
    return get_safety().requires_confirmation(action)


def request_confirmation(action: str, target: str = "", session_id: str = None) -> dict:
    """Solicita confirmacao para acao perigosa."""
    return get_safety().request_confirmation(action, target, session_id)


def check_confirmation(confirmation_id: str, user_response: str) -> dict:
    """Verifica confirmacao do usuario."""
    return get_safety().check_confirmation(confirmation_id, user_response)