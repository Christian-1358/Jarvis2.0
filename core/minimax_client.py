"""
Cliente MiniMax API - Conexão com a API para decisão de ações
"""

import json
import requests
from typing import Optional
from config.settings import MINIMAX_API_KEY, MINIMAX_API_ID, MINIMAX_BASE_URL, MODEL_NAME, API_TIMEOUT


class MiniMaxClient:
    def __init__(self):
        self.api_key = MINIMAX_API_KEY
        self.group_id = MINIMAX_API_ID
        self.base_url = MINIMAX_BASE_URL
        self.model = MODEL_NAME

        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY não configurada!")

    def _get_headers(self) -> dict:
        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
        }
        return headers

    def _build_system_prompt(self) -> str:
        return """Você é o cérebro do Jarvis, um assistente de automação de PC.
Sua tarefa é analisar comandos do usuário e decidir QUAL AÇÃO executar.

## REGRAS:
1. Analise o comando do usuário
2. Identifique a intenção (o que ele quer fazer)
3. Identifique o alvo (sobre o que ele quer fazer)
4. Retorne SOMENTE um JSON com a ação决定

## AÇÕES DISPONÍVEIS (use exatamente estes nomes):

### Sistema:
- search_web: Pesquisar no Google. params: query
- open_app: Abrir aplicativo. params: app_name
- open_site: Abrir site no navegador. params: url
- close_app: Fechar aplicativo. params: app_name
- shutdown_pc: Desligar o PC imediatamente. params: (none)
- schedule_shutdown: Agendar desligamento. params: minutes (número de minutos)
- cancel_shutdown: Cancelar desligamento agendado. params: (none)
- restart_pc: Reiniciar o PC. params: (none)
- hibernate_pc: Hibernar o PC. params: (none)
- sleep_mode: Colocar em modo de suspensão. params: (none)
- wifi_on: Ligar WiFi. params: (none)
- wifi_off: Desligar WiFi. params: (none)
- set_brightness: Definir brilho. params: level (0-100)

### Volume e Mídia:
- volume_up: Aumentar volume. params: (none)
- volume_down: Diminuir volume. params: (none)
- mute: Mutar som. params: (none)
- spotify_play: Tocar música no Spotify. params: (none)
- spotify_pause: Pausar Spotify. params: (none)
- spotify_next: Próxima música. params: (none)
- spotify_previous: Música anterior. params: (none)

### Arquivos:
- open_folder: Abrir pasta. params: path
- create_file: Criar arquivo. params: filename, content
- read_file: Ler arquivo. params: path
- delete_file: Deletar arquivo. params: path
- rename_file: Renomear arquivo. params: old_path, new_name
- move_file: Mover arquivo. params: source, destination
- copy_file: Copiar arquivo. params: source, destination
- organize_folder: Organizar arquivos na pasta. params: path
- find_file: Buscar arquivo. params: name

### Git:
- git_status: Ver status do git. params: (none)
- git_log: Ver histórico do git. params: (none)
- git_pull: Fazer git pull. params: (none)
- git_push: Fazer git push. params: (none)
- git_commit: Fazer commit. params: message

### Monitoramento:
- hardware_status: Ver status do hardware (CPU, memória). params: (none)
- disk_health: Ver saúde do disco. params: (none)
- internet_speed: Testar velocidade da internet. params: (none)

### Automação de Tela:
- type_text: Digitar texto. params: text
- press_key: Pressionar tecla. params: keys
- click_mouse: Clicar com mouse. params: (none)
- move_mouse: Mover mouse. params: x, y
- hotkey: Atalho de teclado. params: keys
- screenshot: Tirar screenshot. params: (none)

### Lembretes e Tarefas:
- add_reminder: Adicionar lembrete. params: text
- list_reminders: Listar lembretes. params: (none)
- add_task: Adicionar tarefa. params: text
- list_tasks: Listar tarefas. params: (none)

### Despertador:
- set_alarm: Definir alarme/despertador. params: time (ex: "14:30" ou "14"), recurring (opcional: "diario" para diária)
- cancel_alarm: Cancelar alarme. params: time (ex: "14:30") ou vazio para cancelar todos
- list_alarms: Listar alarmes ativos. params: (none)
- play_alarm_sound: Tocar som do alarme. params: (none)

### Programação:
- generate_code: Gerar código em uma linguagem. params: language, description
- fix_bugs: Corrigir bugs em código. params: code, language
- refactor_code: Refatorar código. params: code, language
- generate_html: Gerar código HTML. params: description
- generate_css: Gerar código CSS. params: description
- generate_api: Gerar estrutura de API. params: framework, name

### VS Code:
- vscode_create_project: Criar projeto no VS Code. params: project_name, template
- vscode_edit_file: Editar arquivo no VS Code. params: file_path, content
- vscode_install_extension: Instalar extensão no VS Code. params: extension_id
- vscode_open: Abrir arquivo/pasta no VS Code. params: path

### Navegador:
- browser_automate: Automatizar tarefa no navegador. params: task
- browser_fill_form: Preencher formulário web. params: url, fields
- browser_navigate: Navegar para URL. params: url

### GitHub:
- github_auto_commit: Commit automático com mensagem gerada. params: (none)
- github_auto_push: Push automático. params: (none)
- github_auto_pull: Pull automático. params: (none)

### Agenda:
- add_event: Adicionar evento. params: title, date
- calendar_today: Ver eventos de hoje. params: (none)

### Despesas:
- add_expense: Adicionar despesa. params: amount, description
- expense_summary: Ver resumo de despesas. params: (none)

### Informações:
- news: Ver notícias. params: (none)
- weather: Ver clima. params: city

### Comunicação:
- email_summary: Resumo de emails. params: (none)
- check_new_emails: Verificar emails novos. params: (none)
- whatsapp_send: Enviar mensagem WhatsApp. params: to, message
- whatsapp_list_unread: Listar mensagens não lidas. params: (none)
- send_telegram: Enviar mensagem no Telegram. params: message

### Deploy/Backup:
- deploy: Fazer deploy. params: (none)
- backup_dotfiles: Fazer backup dos dotfiles. params: (none)
- schedule_deploy: Agendar deploy para uma hora. params: time (ex: "14:30" ou "14"), recurring (opcional: "diario" para diária)
- cancel_deploy_schedule: Cancelar deploy agendado. params: time (ex: "14:30") ou vazio para cancelar todos
- list_deploy_schedules: Listar deploys agendados. params: (none)

### Stats/ML:
- show_stats: Ver estatísticas de uso. params: (none)
- show_ml_stats: Ver estatísticas de ML (comandos mais usados). params: (none)
- train_ml: Treinar o modelo de ML. params: (none)
- training_status: Ver status do treinamento. params: (none)
- feedback: Registrar feedback para melhorar o modelo. params: command, predicted, correct, rating

### Aprendizado por Reforço (RL):
- rl_reward: Registrar recompensa para uma ação. params: action, reward_type (correct/incorrect/neutral), context
- rl_approve: Aprovar uma ação (recompensa +1.0). params: action, context
- rl_reject: Rejeitar uma ação (recompensa -0.5). params: action, context
- rl_report: Ver relatório completo do RL. params: (none)
- rl_stats: Ver estatísticas de uma ação. params: action

### Análise de Projetos:
- analyze_project: Analisar um projeto completo. params: path (caminho do projeto)
- analyzer_report: Ver relatório do sistema de análise. params: (none)
- analyzer_ml_status: Ver status do ML do analyzer. params: (none)
- analyzer_feedback: Registrar feedback sobre análise. params: issue_type, rule_id, accepted, fixed

### Comandos:
- run_command: Executar comando no terminal. params: command

### Chat:
- chat: Conversa livre (não requer automação). params: (none) - use target para a resposta

## FORMATO DE RESPOSTA:
Retorne APENAS JSON válido, sem markdown, sem explicações:
{"action": "nome_da_acao", "target": "alvo", "parameters": {"chave": "valor"}}

Se o usuário quiser algo que não está nas ações disponíveis ou for só conversa:
{"action": "chat", "target": "sua resposta", "parameters": {}}

## EXEMPLOS:
- "jarvis pesquise sobre Python"
  → {"action": "search_web", "target": "Python", "parameters": {}}

- "jarvis abra o chrome"
  → {"action": "open_app", "target": "chrome", "parameters": {}}

- "jarvis tire um print"
  → {"action": "screenshot", "target": "", "parameters": {}}

- "jarvis quanto tá o dólar"
  → {"action": "chat", "target": "Não tenho acesso a dados financeiros em tempo real.", "parameters": {}}

- "jarvis adiciona tarefa terminar relatório"
  → {"action": "add_task", "target": "terminar relatório", "parameters": {}}
"""

    def analyze_command(self, user_command: str) -> dict:
        command = user_command
        if command.lower().startswith("jarvis"):
            command = command[len("jarvis"):].strip()
        if command.lower().startswith("oi jarvis"):
            command = command[len("oi jarvis"):].strip()

        if not command:
            return {"action": "chat", "target": "Olá! Como posso ajudar?", "parameters": {}}

        system_prompt = self._build_system_prompt()

        try:
            url = f"{self.base_url}/messages"

            payload = {
                "model": self.model,
                "max_tokens": 500,
                "system": system_prompt,
                "messages": [
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