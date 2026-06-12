"""
Cliente MiniMax API - Conexão com a API para decisão de ações
Versão melhorada com contexto, plano e validação
"""

import json
import re
import requests
from typing import Optional, Dict, List, Any
from config.settings import MINIMAX_API_KEY, MINIMAX_API_ID, MINIMAX_BASE_URL, MODEL_NAME, API_TIMEOUT


class MiniMaxClient:
    def __init__(self):
        self.api_key = MINIMAX_API_KEY
        self.group_id = MINIMAX_API_ID
        self.base_url = MINIMAX_BASE_URL
        self.model = MODEL_NAME
        self._context_cache = ""

        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY não configurada!")

    def _get_headers(self) -> dict:
        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
        }
        return headers

    def _get_conversation_context(self) -> str:
        """Obtém contexto das últimas conversas do banco de dados."""
        try:
            from data.core_database import get_jarvis_db
            db = get_jarvis_db()
            if db:
                history = db.get_conversation_history(self.group_id or "default", limit=5)
                if history:
                    lines = ["Conversas recentes:"]
                    for h in reversed(history[-5:]):
                        role = "Usuário" if h.get('role') == 'user' else "Jarvis"
                        msg = h.get('message', '')[:100]
                        action = h.get('action', '')
                        lines.append(f"- {role}: {msg} ({action})")
                    return "\n".join(lines)
        except:
            pass
        return ""

    def _get_workspace_context(self) -> str:
        """Obtém contexto do workspace ativo."""
        try:
            if CONTEXT_BUILDER_AVAILABLE:
                from data.context_builder import context_builder
                ws = context_builder.workspace_memory.get_active_workspace()
                if ws:
                    pending = context_builder.workspace_memory.get_pending_tasks(ws.id)
                    recent = context_builder.workspace_memory.get_recent_actions(ws.id, limit=3)
                    ctx = [f"Workspace ativo: {ws.name}"]
                    if pending:
                        ctx.append(f"Tarefas pendentes: {', '.join(t.title for t in pending[:3])}")
                    if recent:
                        ctx.append(f"Ações recentes: {recent[0].action}")
                    return " | ".join(ctx)
        except:
            pass
        return ""

    def _get_user_preferences(self) -> str:
        """Obtém preferências aprendidas do usuário."""
        try:
            from data.core_database import get_jarvis_db
            db = get_jarvis_db()
            if db:
                prefs = db.search_memories("preferência", category="preference")
                if prefs:
                    return "Preferências: " + ", ".join(p['value'] for p in prefs[:3])
        except:
            pass
        return ""

    def _build_context_prompt(self) -> str:
        """Constrói contexto dinâmico para o prompt."""
        parts = []

        ws_ctx = self._get_workspace_context()
        if ws_ctx:
            parts.append(f"[WORKSPACE] {ws_ctx}")

        conv_ctx = self._get_conversation_context()
        if conv_ctx:
            parts.append(f"[HISTÓRICO] {conv_ctx}")

        prefs = self._get_user_preferences()
        if prefs:
            parts.append(f"[PREFERÊNCIAS] {prefs}")

        return "\n".join(parts) if parts else ""

    def _build_system_prompt(self, user_command: str = "") -> str:
        """Constrói prompt do sistema com contexto dinâmico."""
        context = self._build_context_prompt()
        context_section = ("\n\n## CONTEXTO ATUAL:\n" + context + "\n") if context else "\n"

        base = """Você é o Jarvis, um assistente de automação de PC inteligente.
Sua tarefa é analisar comandos do usuário, entender a INTENÇÃO real por trás das palavras,
e executar a ação mais adequada.

## FLUXO DE RACIOCÍNIO (pense antes de agir):
1. ENTENDER: O que o usuário quer realmente fazer?
2. PLANEJAR: Qual a melhor sequência de ações?
3. EXECUTAR: Execute com precisão
4. VALIDAR: A ação teve o efeito esperado?

"""

        return base + context_section + self._build_actions_prompt() + """

## FORMATO DE RESPOSTA:
Retorne APENAS JSON válido, sem markdown, sem explicações:
{"action": "nome_da_acao", "target": "alvo", "parameters": {"chave": "valor"}}

Se o usuário quiser algo que não está nas ações disponíveis ou for só conversa, use chat.

## EXEMPLOS DE INTERPRETAÇÃO INTELIGENTE:
- "jarvis fecha aquilo" -> usar contexto para identificar "aquilo" = último app aberto
- "jarvis abre o google" -> {"action": "open_app", "target": "chrome", "parameters": {}}
- "jarvis me ajuda" -> {"action": "chat", "target": "Claro! Em que posso ajudar?", "parameters": {}}
- "jarvis pesquisa python" -> {"action": "search_web", "target": "python", "parameters": {}}
"""

    def _build_actions_prompt(self) -> str:
        """Gera seção de ações dinamicamente via ActionRegistry."""
        from core.action_registry import get_action_registry
        registry = get_action_registry()

        rules = """## REGRAS DE ENTENDIMENTO:
- Comandos vagos como "abre o chrome" ou "roda isso" devem ser interpretados corretamente
- Referências como "ele", "lá", "aquilo" devem ser resolvidas pelo contexto
- Se há ambiguidade, escolha a ação mais provável E explain sua escolha
- Quando não souber, peça esclarecimento
"""
        return rules + registry.generate_prompt_section()

    def _preprocess_command(self, command: str) -> str:
        """Pré-processa o comando para melhorar interpretação."""
        import re

        # Normalizar
        command = command.lower().strip()

        # Remover wake words
        for ww in ["jarvis", "oi jarvis", "ei jarvis", "ó jarvis"]:
            if command.startswith(ww):
                command = command[len(ww):].strip()

        # Mapeamento de comandos vagos para ações específicas
        vague_mapping = {
            r'\bpesquis[ae]\b': 'search_web',
            r'\bpesquisa\b': 'search_web',
            r'\bbusca\b': 'search_web',
            r'\bprocura\b': 'search_web',
            r'\babre\b': 'open_app',
            r'\babrir\b': 'open_app',
            r'\baberta\b': 'open_app',
            r'\babra\b': 'open_app',
            r'\bfecha\b': 'close_app',
            r'\bfechar\b': 'close_app',
            r'\bfeche\b': 'close_app',
            r'\bencerr[ae]\b': 'close_app',
            r'\bprint\b': 'screenshot',
            r'\bfoto\b': 'screenshot',
            r'\bcaptura\b': 'screenshot',
        }

        # Mapear apps conhecidos
        app_mapping = {
            'google': 'chrome',
            'chrome': 'chrome',
            'whatsapp': 'whatsapp',
            'terminal': 'terminal',
            'vscode': 'code',
            'code': 'code',
            'spotify': 'spotify',
            'arquivos': 'nautilus',
            'files': 'nautilus',
        }

        return command

    def _build_conversation_history(self, user_command: str) -> List[dict]:
        """Constrói histórico de conversa para contexto."""
        messages = []

        # Adicionar contexto do workspace se disponível
        ws_context = self._get_workspace_context()
        if ws_context:
            messages.append({
                "role": "user",
                "content": [{"type": "text", "text": f"[Contexto atual: {ws_context}]"}]
            })

        return messages

    def analyze_command(self, user_command: str) -> dict:
        command = user_command
        if command.lower().startswith("jarvis"):
            command = command[len("jarvis"):].strip()
        if command.lower().startswith("oi jarvis"):
            command = command[len("oi jarvis"):].strip()

        if not command:
            return {"action": "chat", "target": "Olá! Como posso ajudar?", "parameters": {}}

        # Pré-processar comando
        command = self._preprocess_command(command)

        # Construir prompt com contexto dinâmico
        system_prompt = self._build_system_prompt(command)
        conversation_history = self._build_conversation_history(command)

        try:
            url = f"{self.base_url}/messages"

            payload = {
                "model": self.model,
                "max_tokens": 600,
                "system": system_prompt,
                "messages": conversation_history + [
                    {"role": "user", "content": [{"type": "text", "text": command}]}
                ]
            }

            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=API_TIMEOUT
            )

            if response.status_code != 200:
                print(f"[ERRO API] Status: {response.status_code}")
                print(f"[ERRO API] Resposta: {response.text}")
                return {"action": "error", "target": f"Erro na API: {response.status_code}", "parameters": {}}

            result = response.json()

            content = ""
            thinking_content = ""
            if "content" in result:
                for item in result["content"]:
                    if item.get("type") == "text":
                        content = item.get("text", "")
                        break
                    elif item.get("type") == "thinking":
                        thinking_content = item.get("thinking", "")

            # Se não encontrou text, tenta usar o thinking (pode conter a resposta)
            if not content and thinking_content:
                # O thinking pode conter o JSON que precisamos
                content = thinking_content

            if content:
                content = content.strip()
                if content.startswith("```"):
                    lines = content.split("\n")
                    content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

                parsed = json.loads(content)
                return parsed

            return {"action": "chat", "target": "Não consegui entender o comando.", "parameters": {}}

        except json.JSONDecodeError as e:
            print(f"[ERRO JSON] {e}")
            return {"action": "chat", "target": f"Erro ao processar resposta: {e}", "parameters": {}}

        except requests.exceptions.Timeout:
            return {"action": "error", "target": "Timeout na comunicação com a API", "parameters": {}}

        except Exception as e:
            print(f"[ERRO] {e}")
            return {"action": "error", "target": str(e), "parameters": {}}

    def _call_llm(self, prompt: str) -> str:
        """Faz uma chamada direta ao LLM para geração de conteúdo."""
        try:
            url = f"{self.base_url}/messages"
            payload = {
                "model": self.model,
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
            }
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=API_TIMEOUT)
            if response.status_code == 200:
                result = response.json()
                for item in result.get("content", []):
                    if item.get("type") == "text":
                        return item.get("text", "")
            return ""
        except Exception as e:
            print(f"[ERRO LLM] {e}")
            return ""


_client: Optional[MiniMaxClient] = None


def get_client() -> MiniMaxClient:
    global _client
    if _client is None:
        _client = MiniMaxClient()
    return _client


def analyze_command(command: str) -> dict:
    return get_client().analyze_command(command)


# Flag para verificar se context_builder está disponível
try:
    from data.context_builder import context_builder
    CONTEXT_BUILDER_AVAILABLE = True
except ImportError:
    CONTEXT_BUILDER_AVAILABLE = False