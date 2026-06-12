"""
Action Registry - Single Source of Truth para todas as acoes do Jarvis.

Elimina duplicacao entre:
- functions/__init__.py (FUNCTIONS dict)
- tool_registry.py (category_map)
- safety.py (DANGEROUS_ACTIONS)
- minimax_client.py (hardcoded prompt)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Callable, Optional
from datetime import datetime


@dataclass
class ActionDefinition:
    name: str
    function: Callable
    description: str
    category: str
    parameters: List[str] = field(default_factory=list)
    requires_target: bool = False
    contexts: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    is_dangerous: bool = False
    risk_level: str = "low"
    confirmation_phrase: Optional[str] = None
    use_count: int = 0
    success_rate: float = 0.0
    last_used: Optional[datetime] = None

    def __call__(self, *args, **kwargs) -> str:
        try:
            self.use_count += 1
            self.last_used = datetime.now()
            return self.function(*args, **kwargs)
        except Exception as e:
            return f"Erro ao executar {self.name}: {e}"

    def mark_success(self):
        self.use_count += 1
        if self.use_count == 1:
            self.success_rate = 1.0
        else:
            self.success_rate = (self.success_rate * (self.use_count - 2) + 1.0) / (self.use_count - 1)

    def mark_failure(self):
        self.use_count += 1
        if self.use_count == 1:
            self.success_rate = 0.0
        else:
            self.success_rate = (self.success_rate * (self.use_count - 2) + 0.0) / (self.use_count - 1)


@dataclass
class DangerousActionInfo:
    phrase: str
    risk_level: str
    description: str


DANGEROUS_ACTIONS: Dict[str, DangerousActionInfo] = {
    "shutdown_pc": DangerousActionInfo("sim, desligar", "critical", "Desliga o PC imediatamente"),
    "restart_pc": DangerousActionInfo("sim, reiniciar", "high", "Reinicia o PC"),
    "hibernate_pc": DangerousActionInfo("sim, hibernar", "medium", "Hiberna o PC"),
    "delete_file": DangerousActionInfo("sim, apagar", "high", "Deleta arquivo permanentemente"),
    "format_disk": DangerousActionInfo("IMPOSSIBLE", "critical", "Formata disco (irreversivel)"),
    "run_command": DangerousActionInfo("sim, executar", "high", "Executa comando no terminal"),
    "drop_database": DangerousActionInfo("IMPOSSIBLE", "critical", "Drop de banco de dados"),
}


def is_dangerous_action(action_name: str) -> bool:
    return action_name in DANGEROUS_ACTIONS


def requires_confirmation_action(action_name: str) -> bool:
    info = DANGEROUS_ACTIONS.get(action_name)
    if not info:
        return False
    return info.risk_level in ("high", "critical")


def get_danger_info(action_name: str) -> Optional[DangerousActionInfo]:
    return DANGEROUS_ACTIONS.get(action_name)


ACTION_CATEGORIES: Dict[str, List[str]] = {
    "system": ["shutdown_pc", "restart_pc", "hibernate_pc", "sleep_mode", "wifi_on", "wifi_off", "set_brightness"],
    "apps": ["open_app", "close_app", "open_site"],
    "search": ["search_web", "find_file"],
    "files": ["open_folder", "create_file", "read_file", "delete_file", "rename_file", "move_file", "copy_file", "organize_folder"],
    "git": ["git_status", "git_log", "git_pull", "git_push", "git_commit"],
    "monitoring": ["hardware_status", "disk_health", "internet_speed"],
    "automation": ["type_text", "press_key", "click_mouse", "move_mouse", "hotkey", "screenshot"],
    "productivity": ["add_reminder", "list_reminders", "add_task", "list_tasks"],
    "calendar": ["add_event", "calendar_today"],
    "finance": ["add_expense", "expense_summary"],
    "stats": ["show_stats", "show_ml_stats", "train_ml"],
    "rl": ["rl_report", "rl_stats"],
    "deploy": ["deploy", "backup_dotfiles", "schedule_deploy", "cancel_deploy_schedule", "list_deploy_schedules"],
    "terminal": ["run_command"],
    "communication": ["whatsapp_send", "whatsapp_list_unread", "send_telegram"],
    "alarm": ["set_alarm", "cancel_alarm", "list_alarms", "play_alarm_sound"],
    "code": ["generate_code", "fix_bugs", "refactor_code", "generate_html", "generate_css", "generate_api"],
    "vscode": ["vscode_create_project", "vscode_edit_file", "vscode_install_extension", "vscode_open"],
    "browser": ["browser_automate", "browser_fill_form", "browser_navigate"],
    "github": ["github_auto_commit", "github_auto_push", "github_auto_pull"],
    "media": ["spotify_play", "spotify_pause", "spotify_next", "spotify_previous"],
    "volume": ["volume_up", "volume_down", "mute"],
    "info": ["news", "weather"],
    "email": ["email_summary", "check_new_emails"],
}

ACTIONS_REQUIRING_TARGET = {
    "open_folder", "create_file", "read_file", "delete_file", "rename_file", "move_file", "copy_file", "find_file",
    "open_site", "add_task", "add_reminder", "add_expense", "git_commit", "run_command", "add_event", "whatsapp_send",
    "send_telegram", "set_alarm", "generate_code", "fix_bugs", "refactor_code", "generate_html", "generate_css",
    "generate_api", "vscode_create_project", "vscode_edit_file", "vscode_install_extension", "vscode_open",
    "browser_automate", "browser_fill_form", "browser_navigate", "spotify_play", "weather"
}


class ActionRegistry:
    def __init__(self):
        self._actions: Dict[str, ActionDefinition] = {}
        self._loaded: bool = False

    def register(self, action: ActionDefinition):
        self._actions[action.name] = action

    def register_action(self, name: str, function: Callable, description: str = "", category: str = "general",
                        parameters: List[str] = None, contexts: List[str] = None, examples: List[str] = None,
                        requires_target: bool = None, is_dangerous: bool = None, risk_level: str = "low"):
        if parameters is None:
            parameters = []
        if contexts is None:
            contexts = []
        if examples is None:
            examples = []

        if requires_target is None:
            requires_target = name in ACTIONS_REQUIRING_TARGET
        if is_dangerous is None:
            is_dangerous = name in DANGEROUS_ACTIONS

        danger_info = DANGEROUS_ACTIONS.get(name)

        action = ActionDefinition(
            name=name,
            function=function,
            description=description or function.__doc__ or f"Acao {name}",
            category=category,
            parameters=parameters,
            requires_target=requires_target,
            contexts=contexts,
            examples=examples,
            is_dangerous=is_dangerous,
            risk_level=risk_level if not danger_info else danger_info.risk_level,
            confirmation_phrase=danger_info.phrase if danger_info else None
        )
        self._actions[name] = action

    def get(self, name: str) -> Optional[ActionDefinition]:
        return self._actions.get(name)

    def list_all(self) -> Dict[str, ActionDefinition]:
        return dict(self._actions)

    def list_by_category(self, category: str) -> List[ActionDefinition]:
        return [a for a in self._actions.values() if a.category == category]

    def get_categories(self) -> List[str]:
        cats = set(a.category for a in self._actions.values())
        return sorted(cats)

    def get_all_action_names(self) -> List[str]:
        return list(self._actions.keys())

    def load_from_functions_module(self):
        if self._loaded:
            return

        try:
            from functions import FUNCTIONS

            for name, func in FUNCTIONS.items():
                category = "general"
                contexts = []
                examples = []

                for cat, actions in ACTION_CATEGORIES.items():
                    if name in actions:
                        category = cat
                        break

                if name in DANGEROUS_ACTIONS:
                    contexts.append("dangerous")
                if category != "general":
                    contexts.append(category)

                self.register_action(
                    name=name,
                    function=func,
                    description=func.__doc__ or f"Funcao {name}",
                    category=category,
                    contexts=contexts,
                    examples=examples
                )

            self._loaded = True

        except ImportError as e:
            print(f"[ACTION REGISTRY] Erro ao carregar: {e}")

    def generate_prompt_section(self) -> str:
        lines = ["## ACOES DISPONIVEIS (use exatamente estes nomes):", ""]

        for category in sorted(self.get_categories()):
            actions = self.list_by_category(category)
            if not actions:
                continue

            lines.append(f"### {category.upper()}:")
            for action in sorted(actions, key=lambda a: a.name):
                params_str = ", ".join(f"params: {', '.join(action.parameters)}") if action.parameters else "params: (none)"
                lines.append(f"- {action.name}: {action.description}. {params_str}")
            lines.append("")

        return "\n".join(lines)


_registry: Optional[ActionRegistry] = None


def get_action_registry() -> ActionRegistry:
    global _registry
    if _registry is None:
        _registry = ActionRegistry()
        _registry.load_from_functions_module()
    return _registry


def reload_action_registry():
    global _registry
    _registry = None
    return get_action_registry()