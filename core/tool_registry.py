"""
Jarvis Tool Registry - Sistema Centralizado de Ferramentas

Agora usa action_registry.py como source of truth para:
- Categorias de ações (ACTION_CATEGORIES)
- Ações perigosas (DANGEROUS_ACTIONS)
- Geração de prompts

Mantém compatibilidade com a API existente (Tool, ToolRegistry).
"""

from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

# Importar do action_registry (source of truth)
from core.action_registry import (
    ActionRegistry,
    ActionDefinition,
    DANGEROUS_ACTIONS,
    ACTION_CATEGORIES,
    ACTIONS_REQUIRING_TARGET,
    get_action_registry,
    is_dangerous_action,
    requires_confirmation_action as action_requires_confirmation,
)


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
    contexts: List[str] = field(default_factory=list)
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
    """
    Registro centralizado de todas as ferramentas do Jarvis.

    Agora delega para ActionRegistry como source of truth.
    Mantém API existente para compatibilidade.
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[str, List[str]] = {}
        self._action_registry = get_action_registry()
        self._load_tools()

    def _load_tools(self):
        """Carrega ferramentas do ActionRegistry."""
        action_reg = self._action_registry

        for name, action_def in action_reg.list_all().items():
            tool = Tool(
                name=action_def.name,
                function=action_def.function,
                description=action_def.description,
                category=action_def.category,
                parameters=action_def.parameters,
                requires_target=action_def.requires_target,
                is_dangerous=action_def.is_dangerous,
                requires_confirmation=action_def.is_dangerous,
                contexts=action_def.contexts,
                examples=action_def.examples
            )
            self._tools[name] = tool

            if action_def.category not in self._categories:
                self._categories[action_def.category] = []
            self._categories[action_def.category].append(name)

    def register(self, name: str, function: Callable, description: str = "",
                 category: str = "general", parameters: List[str] = None,
                 requires_target: bool = False, is_dangerous: bool = False,
                 contexts: List[str] = None, examples: List[str] = None):
        """
        Registra uma nova ferramenta.

        Nota: Para novas ações, considere usar ActionRegistry diretamente.
        """
        if parameters is None:
            parameters = []
        if contexts is None:
            contexts = []
        if examples is None:
            examples = []

        # Verificar se é perigosa via ActionRegistry
        is_dangerous = is_dangerous or is_dangerous_action(name)

        tool = Tool(
            name=name,
            function=function,
            description=description,
            category=category,
            parameters=parameters,
            requires_target=requires_target,
            is_dangerous=is_dangerous,
            requires_confirmation=is_dangerous,
            contexts=contexts,
            examples=examples
        )

        self._tools[name] = tool

        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(name)

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
            if tool.requires_target:
                params['target'] = target

            if params:
                result = tool.function(**params)
            elif tool.requires_target and target:
                result = tool.function(target)
            else:
                result = tool.function()

            if "erro" not in result.lower()[:20]:
                tool.mark_success()
            else:
                tool.mark_failure()

            return result

        except TypeError as e:
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
        return is_dangerous_action(name)

    def needs_confirmation(self, name: str) -> bool:
        """Verifica se uma ação precisa de confirmação."""
        return action_requires_confirmation(name)

    def get_top_tools(self, limit: int = 10) -> List[Tool]:
        """Retorna ferramentas mais usadas."""
        sorted_tools = sorted(self._tools.values(), key=lambda t: t.use_count, reverse=True)
        return sorted_tools[:limit]

    def get_stats(self) -> dict:
        """Retorna estatísticas do registry."""
        total_tools = len(self._tools)
        total_uses = sum(t.use_count for t in self._tools.values())
        dangerous_count = len(DANGEROUS_ACTIONS)

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

    def generate_prompt_section(self) -> str:
        """Gera seção de ações para o prompt (delega para ActionRegistry)."""
        return self._action_registry.generate_prompt_section()


# Instância global
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Retorna instância global do registry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


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


def reload_registry():
    """Recarrega o registry (para desenvolvimento)."""
    global _registry
    _registry = None
    return get_registry()