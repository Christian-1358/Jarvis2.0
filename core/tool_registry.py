"""
Jarvis Tool Registry - Sistema Centralizado de Ferramentas
取代 if/else espalhados por registro centralizado de ações
Escalável, documentado e fácil de estender
"""

from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Tool:
    """Representa uma ferramenta/ação do Jarvis."""
    name: str
    function: Callable
    description: str
    category: str
    parameters: List[str] = field(default_factory=list)
    requires_target: bool = False
    is_dangerous: bool = False
    requires_confirmation: bool = False
    contexts: List[str] = field(default_factory=list)  # browser, search, git, system, files, etc
    examples: List[str] = field(default_factory=list)
    use_count: int = 0
    success_rate: float = 0.0
    last_used: Optional[datetime] = None

    def __call__(self, *args, **kwargs) -> str:
        """Executa a ferramenta."""
        try:
            self.use_count += 1
            self.last_used = datetime.now()
            return self.function(*args, **kwargs)
        except Exception as e:
            return f"Erro ao executar {self.name}: {e}"

    def mark_success(self):
        """Marca uso bem-sucedido."""
        self.use_count += 1
        if self.use_count == 1:
            self.success_rate = 1.0
        else:
            self.success_rate = (self.success_rate * (self.use_count - 2) + 1.0) / (self.use_count - 1)

    def mark_failure(self):
        """Marca uso falho."""
        self.use_count += 1
        if self.use_count == 1:
            self.success_rate = 0.0
        else:
            self.success_rate = (self.success_rate * (self.use_count - 2) + 0.0) / (self.use_count - 1)


class ToolRegistry:
    """Registro centralizado de todas as ferramentas do Jarvis."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[str, List[str]] = {}
        self._dangerous_actions: set = set()
        self._init_core_tools()

    def _init_core_tools(self):
        """Inicializa ferramentas base do sistema."""
        #_tools.py será importado e suas funções registradas aqui
        pass

    def register(self, name: str, function: Callable, description: str = "",
                 category: str = "general", parameters: List[str] = None,
                 requires_target: bool = False, is_dangerous: bool = False,
                 contexts: List[str] = None, examples: List[str] = None):
        """Registra uma nova ferramenta."""
        tool = Tool(
            name=name,
            function=function,
            description=description,
            category=category,
            parameters=parameters or [],
            requires_target=requires_target,
            is_dangerous=is_dangerous,
            requires_confirmation=is_dangerous,
            contexts=contexts or [],
            examples=examples or []
        )

        self._tools[name] = tool

        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(name)

        if is_dangerous:
            self._dangerous_actions.add(name)

    def get(self, name: str) -> Optional[Tool]:
        """Retorna uma ferramenta pelo nome."""
        return self._tools.get(name)

    def execute(self, name: str, target: str = "", parameters: dict = None) -> str:
        """Executa uma ferramenta."""
        tool = self.get(name)
        if not tool:
            return f"Ferramenta desconhecida: {name}"

        if tool.requires_target and not target and not parameters:
            return f"Ferramenta '{name}' requer um alvo (target)"

        params = parameters or {}

        try:
            # Construir args baseado nos parâmetros
            if tool.requires_target:
                params['target'] = target

            if params:
                result = tool.function(**params)
            elif tool.requires_target and target:
                result = tool.function(target)
            else:
                result = tool.function()

            # Atualizar estatísticas
            if "erro" not in result.lower()[:20]:
                tool.mark_success()
            else:
                tool.mark_failure()

            return result

        except TypeError as e:
            # Parâmetros errados - tentar com target
            try:
                result = tool.function(target) if target else tool.function()
                return result
            except Exception as e2:
                return f"Erro ao executar {name}: {e2}"
        except Exception as e:
            tool.mark_failure()
            return f"Erro ao executar {name}: {e}"

    def list_all(self) -> Dict[str, Tool]:
        """Lista todas as ferramentas."""
        return self._tools.copy()

    def list_by_category(self, category: str) -> List[Tool]:
        """Lista ferramentas de uma categoria."""
        names = self._categories.get(category, [])
        return [self._tools[name] for name in names if name in self._tools]

    def list_by_context(self, context: str) -> List[Tool]:
        """Lista ferramentas de um contexto."""
        return [t for t in self._tools.values() if context in t.contexts]

    def get_categories(self) -> List[str]:
        """Lista todas as categorias."""
        return list(self._categories.keys())

    def is_dangerous(self, name: str) -> bool:
        """Verifica se uma ação é perigosa."""
        return name in self._dangerous_actions

    def needs_confirmation(self, name: str) -> bool:
        """Verifica se uma ação precisa de confirmação."""
        tool = self.get(name)
        return tool.requires_confirmation if tool else False

    def get_top_tools(self, limit: int = 10) -> List[Tool]:
        """Retorna ferramentas mais usadas."""
        sorted_tools = sorted(self._tools.values(), key=lambda t: t.use_count, reverse=True)
        return sorted_tools[:limit]

    def get_stats(self) -> dict:
        """Retorna estatísticas do registry."""
        total_tools = len(self._tools)
        total_uses = sum(t.use_count for t in self._tools.values())
        dangerous_count = len(self._dangerous_actions)

        return {
            "total_tools": total_tools,
            "total_uses": total_uses,
            "categories": len(self._categories),
            "dangerous_actions": dangerous_count
        }

    def generate_docs(self) -> str:
        """Gera documentação das ferramentas."""
        lines = ["# Jarvis Tool Registry", "=" * 50, ""]

        for category in self.get_categories():
            lines.append(f"## {category.upper()}")
            lines.append("")
            tools = self.list_by_category(category)
            for tool in tools:
                danger = " [PERIGOSO]" if tool.is_dangerous else ""
                lines.append(f"### {tool.name}{danger}")
                lines.append(f"{tool.description}")
                if tool.contexts:
                    lines.append(f"Contextos: {', '.join(tool.contexts)}")
                if tool.examples:
                    lines.append("Exemplos:")
                    for ex in tool.examples:
                        lines.append(f"  - {ex}")
                lines.append(f"Usos: {tool.use_count} | Taxa de sucesso: {tool.success_rate:.0%}")
                lines.append("")

        return "\n".join(lines)


# Instância global
_registry = None


def get_registry() -> ToolRegistry:
    """Retorna instância global do registry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        _load_tools()
    return _registry


def _load_tools():
    """Carrega todas as ferramentas do módulo functions."""
    try:
        from functions import FUNCTIONS
        registry = get_registry()

        # Mapeamento de categorias
        category_map = {
            # Sistema
            "shutdown_pc": ("system", ["system"], ["desliga o PC", "desligar computador"]),
            "restart_pc": ("system", ["system"], ["reinicia o PC"]),
            "hibernate_pc": ("system", ["system"], ["hibernar"]),
            "sleep_mode": ("system", ["system"], ["suspender"]),
            "wifi_on": ("system", ["system"], ["ligar wifi"]),
            "wifi_off": ("system", ["system"], ["desligar wifi"]),
            "set_brightness": ("system", ["system"], ["brilho"]),

            # Apps
            "open_app": ("apps", ["browser"], ["abre o chrome", "abrir firefox"]),
            "close_app": ("apps", ["browser"], ["fecha o chrome", "fechar navegador"]),
            "open_site": ("apps", ["browser"], ["abre o google", "abrir site"]),

            # Busca
            "search_web": ("search", ["search"], ["pesquisa python", "procure sobre"]),
            "find_file": ("files", ["files"], ["buscar arquivo", "procura arquivo"]),

            # Arquivos
            "open_folder": ("files", ["files"], ["abre pasta", "abrir diretório"]),
            "create_file": ("files", ["files"], ["criar arquivo"]),
            "read_file": ("files", ["files"], ["ler arquivo", "mostra conteúdo"]),
            "delete_file": ("files", ["files", "dangerous"], ["apagar arquivo", "deletar"]),
            "rename_file": ("files", ["files"], ["renomear"]),
            "move_file": ("files", ["files"], ["mover arquivo"]),
            "copy_file": ("files", ["files"], ["copiar arquivo"]),
            "organize_folder": ("files", ["files"], ["organizar pasta"]),

            # Git
            "git_status": ("git", ["git"], ["status git", "git status"]),
            "git_log": ("git", ["git"], ["log git", "git log"]),
            "git_pull": ("git", ["git"], ["git pull"]),
            "git_push": ("git", ["git"], ["git push"]),
            "git_commit": ("git", ["git"], ["git commit"]),

            # Monitoramento
            "hardware_status": ("monitoring", ["system"], ["status hardware", "status do PC"]),
            "disk_health": ("monitoring", ["system"], ["saúde do disco"]),
            "internet_speed": ("monitoring", ["system"], ["velocidade internet"]),

            # Automação
            "type_text": ("automation", ["automation"], ["digitar texto"]),
            "press_key": ("automation", ["automation"], ["pressionar tecla"]),
            "click_mouse": ("automation", ["automation"], ["clique mouse"]),
            "move_mouse": ("automation", ["automation"], ["mover mouse"]),
            "hotkey": ("automation", ["automation"], ["atalho teclado"]),
            "screenshot": ("automation", ["automation"], ["screenshot", "print"]),

            # Lembretes/Tarefas
            "add_reminder": ("productivity", ["productivity"], ["adiciona lembrete"]),
            "list_reminders": ("productivity", ["productivity"], ["lista lembretes"]),
            "add_task": ("productivity", ["productivity"], ["adiciona tarefa"]),
            "list_tasks": ("productivity", ["productivity"], ["lista tarefas"]),

            # Agenda
            "add_event": ("calendar", ["calendar"], ["adiciona evento"]),
            "calendar_today": ("calendar", ["calendar"], ["eventos hoje"]),

            # Despesas
            "add_expense": ("finance", ["finance"], ["adiciona despesa"]),
            "expense_summary": ("finance", ["finance"], ["resumo despesas"]),

            # Stats/ML
            "show_stats": ("stats", ["stats"], ["mostra estatísticas", "stats"]),
            "show_ml_stats": ("stats", ["stats"], ["stats de ML"]),
            "train_ml": ("stats", ["stats"], ["treina modelo"]),
            "rl_report": ("rl", ["rl"], ["relatório RL"]),
            "rl_stats": ("rl", ["rl"], ["stats RL"]),

            # Deploy
            "deploy": ("deploy", ["deploy"], ["fazer deploy"]),
            "backup_dotfiles": ("backup", ["backup"], ["backup dotfiles"]),

            # Comandos
            "run_command": ("terminal", ["terminal"], ["executa comando"]),
        }

        for name, func in FUNCTIONS.items():
            if name in category_map:
                category, contexts, examples = category_map[name]
                is_dangerous = "dangerous" in contexts
                registry.register(
                    name=name,
                    function=func,
                    description=func.__doc__ or f"Função {name}",
                    category=category,
                    contexts=contexts,
                    examples=examples,
                    is_dangerous=is_dangerous,
                    requires_target=name in ["open_folder", "create_file", "read_file", "delete_file",
                                            "rename_file", "move_file", "copy_file", "find_file",
                                            "open_site", "add_task", "add_reminder", "add_expense",
                                            "git_commit", "run_command"]
                )
            else:
                # Registrar sem categoria específica
                registry.register(
                    name=name,
                    function=func,
                    description=func.__doc__ or f"Função {name}",
                    category="general"
                )

    except ImportError as e:
        print(f"[TOOL REGISTRY] Erro ao carregar ferramentas: {e}")


def execute_tool(name: str, target: str = "", parameters: dict = None) -> str:
    """Executa uma ferramenta pelo nome."""
    return get_registry().execute(name, target, parameters)


def list_tools(category: str = None) -> List[Tool]:
    """Lista ferramentas, opcionalmente filtradas por categoria."""
    registry = get_registry()
    if category:
        return registry.list_by_category(category)
    return list(registry.list_all().values())


def get_tool(name: str) -> Optional[Tool]:
    """Retorna uma ferramenta específica."""
    return get_registry().get(name)