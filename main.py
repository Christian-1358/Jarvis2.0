#!/usr/bin/env python3
"""
Jarvis MiniMax v2.0 - Arquitetura Refatorada
Assistente de automação com IA da MiniMax

Fluxo de Execução:
User → Context → Memory → MiniMax → RL → Executor → Feedback → DB

Arquitetura:
- Tool Registry: Registro centralizado de ferramentas
- Safety Manager: Sistema de confirmação para ações perigosas
- Core Database: Persistência SQL unificada
- RL System: Aprendizado por reforço integrado
"""

import sys
import json
import threading
import uuid
from datetime import datetime
from typing import Optional, Tuple

# Tentar importar componentes opcionais
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

TTS_AVAILABLE = EDGE_TTS_AVAILABLE or PYTTSX3_AVAILABLE

try:
    import speech_recognition as sr
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

try:
    from flask import Flask, render_template, request, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False


from config.settings import WAKE_WORD

# Core modules
from core.minimax_client import analyze_command
from core.tool_registry import get_registry, execute_tool, get_tool
from core.safety import get_safety, is_dangerous, requires_confirmation, request_confirmation

# Database - Nova camada unificada
try:
    from data.core_database import get_jarvis_db, JarvisDB
    DB_AVAILABLE = True
except ImportError as e:
    print(f"[DB] Não disponível: {e}")
    DB_AVAILABLE = False
    get_jarvis_db = lambda: None

# ML/R legacy modules (for backward compatibility)
try:
    from ml.command_predictor import add_command
    from ml.usage_analytics import record_action
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

try:
    from ml.reinforcement_learning import reward_action
    RL_AVAILABLE = True
except ImportError:
    RL_AVAILABLE = False

# Context Builder and Workspace Memory
try:
    from data.context_builder import context_builder, AdvancedContextBuilder
    from data.workspace_memory import workspace_memory, conversation_summarizer
    CONTEXT_BUILDER_AVAILABLE = True
except ImportError as e:
    print(f"[CONTEXT] Não disponível: {e}")
    CONTEXT_BUILDER_AVAILABLE = False


class JarvisMiniMax:
    """Jarvis MiniMax - Arquitetura refatorada com fluxo:

    User → Context → Memory → MiniMax → RL → Executor → Feedback → DB
    """

    def __init__(self):
        self.running = True
        self.session_id = str(uuid.uuid4())
        self.tts_engine = None
        self.web_server = None
        self.web_thread = None
        self._command_lock = threading.Lock()
        self._last_command = ""
        self._last_command_time = 0

        # Inicializar Tool Registry
        self.tool_registry = get_registry()

        # Inicializar Safety Manager
        self.safety = get_safety()

        # Inicializar Core Database
        self.db = get_jarvis_db() if DB_AVAILABLE else None

        # Inicializar Context Builder e Workspace Memory
        self.context_builder = None
        if CONTEXT_BUILDER_AVAILABLE:
            try:
                self.context_builder = context_builder
            except Exception as e:
                print(f"[CONTEXT] Erro ao inicializar: {e}")

        # TTS - usa edge-tts com voz neural Antonio (masculino brasileiro)
        self.tts_engine = None
        self.tts_async = None
        if EDGE_TTS_AVAILABLE:
            try:
                import edge_tts
                self.tts_async = edge_tts
                self.tts_voice = "pt-BR-AntonioNeural"
            except Exception:
                self.tts_async = None

        if not self.tts_async and PYTTSX3_AVAILABLE:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty("rate", 150)
                voices = self.tts_engine.getProperty("voices")
                if voices:
                    for v in voices:
                        if 'pt-br' in v.languages:
                            self.tts_engine.setProperty("voice", v.id)
                            break
            except Exception:
                self.tts_engine = None

        # Voice
        self.recognizer = None
        self.microphone = None
        if VOICE_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                self.microphone = sr.Microphone()
            except Exception:
                self.recognizer = None
                self.microphone = None

        # Setup Flask
        self.app = None
        self._setup_web_app()

        # Registrar ações perigosas no DB
        if self.db:
            dangerous_actions = ["shutdown_pc", "restart_pc", "delete_file",
                               "hibernate_pc", "run_command", "format_disk"]
            for action in dangerous_actions:
                self.db.register_dangerous_action(action)

    def _setup_web_app(self) -> None:
        """Configura a aplicação Flask para a interface web."""
        if not FLASK_AVAILABLE:
            return

        self.app = Flask(__name__, template_folder='templates')

        @self.app.route("/")
        def index():
            return render_template("index.html")

        @self.app.route("/api/command", methods=["POST"])
        def send_command():
            try:
                data = request.get_json()
                command = data.get("command", "").strip()
                if not command:
                    return jsonify({"success": False, "error": "Comando vazio"}), 400

                result = self.process_command(command)
                return jsonify({"success": True, "result": result})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/safety/confirm", methods=["POST"])
        def confirm_dangerous():
            try:
                data = request.get_json()
                confirmation_id = data.get("confirmation_id")
                user_response = data.get("response", "")

                result = self.safety.check_confirmation(confirmation_id, user_response)
                return jsonify(result)
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/status")
        def status():
            return jsonify({
                "session_id": self.session_id,
                "tools_loaded": len(self.tool_registry.list_all()),
                "db_available": DB_AVAILABLE,
                "ml_available": ML_AVAILABLE,
                "rl_available": RL_AVAILABLE
            })

        @self.app.route("/api/voice-mode-status")
        def voice_mode_status():
            return jsonify({"running": False})

        @self.app.route("/api/voice-preview", methods=["POST"])
        def voice_preview():
            return jsonify({"success": True})

    def start_web_server(self, port: int = 5000) -> None:
        """Inicia o servidor web em uma thread separada."""
        if not FLASK_AVAILABLE:
            print("[WEB] Flask não disponível. Instale com: pip install flask")
            return

        def run_server():
            print(f"[WEB] Jarvis Web rodando em http://localhost:{port}")
            self.app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

        self.web_thread = threading.Thread(target=run_server, daemon=True)
        self.web_thread.start()

    def stop_web_server(self) -> None:
        """Para o servidor web."""
        self.running = False

    def speak(self, text: str) -> None:
        """Output de texto com TTS opcional (sem print, só áudio)."""
        if not text or not text.strip():
            return
        if self.tts_async:
            try:
                import asyncio
                import subprocess
                # Limpar texto de caracteres problemáticos
                clean_text = text.strip()
                async def speak_async():
                    communicate = self.tts_async.Communicate(clean_text, self.tts_voice)
                    await communicate.save("/tmp/jarvis_speak.mp3")
                asyncio.run(speak_async())
                # Aguarda arquivo estar pronto
                import time
                time.sleep(0.5)
                # Verifica se arquivo existe e tem conteúdo
                import os
                if os.path.exists("/tmp/jarvis_speak.mp3") and os.path.getsize("/tmp/jarvis_speak.mp3") > 0:
                    subprocess.run(["paplay", "/tmp/jarvis_speak.mp3"],
                                  capture_output=True, timeout=10)
            except Exception as e:
                print(f"[TTS ERRO] {e}")
        elif self.tts_engine:
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception:
                pass

    def listen(self) -> Optional[str]:
        """Escuta comando de voz."""
        if not VOICE_AVAILABLE or not self.recognizer or not self.microphone:
            print("[JARVIS] Modo voz não disponível.")
            return None

        print("[JARVIS] Ouvindo...")

        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)

            text = self.recognizer.recognize_google(audio, language="pt-BR")
            print(f"[VOZ] {text}")
            return text
        except Exception as e:
            print(f"[ERRO] {e}")
            return None

    def _detect_context(self, action: str) -> str:
        """Detecta o contexto de uma ação para RL."""
        context_map = {
            "browser": ["open_app", "close_app", "browser_navigate", "open_site"],
            "search": ["search_web", "find_file"],
            "git": ["git_status", "git_log", "git_pull", "git_push", "git_commit"],
            "system": ["hardware_status", "disk_health", "internet_speed", "shutdown_pc",
                      "restart_pc", "hibernate_pc", "sleep_mode", "wifi_on", "wifi_off"],
            "files": ["open_folder", "create_file", "read_file", "delete_file",
                     "rename_file", "move_file", "copy_file", "organize_folder"],
            "automation": ["type_text", "press_key", "click_mouse", "move_mouse",
                         "hotkey", "screenshot"],
            "productivity": ["add_reminder", "list_reminders", "add_task", "list_tasks",
                           "add_event", "calendar_today"],
            "stats": ["show_stats", "show_ml_stats", "rl_report", "rl_stats", "train_ml"]
        }

        for context, actions in context_map.items():
            if action in actions:
                return context
        return "general"

    def _handle_workspace_command(self, command: str) -> str:
        """Processa comandos relacionados a workspaces."""
        if not self.context_builder:
            return "Sistema de workspace não disponível."

        command_lower = command.lower()

        try:
            # Criar workspace
            if "criar workspace" in command_lower or "novo projeto" in command_lower:
                # Extrair nome do projeto
                name = command.replace("criar workspace", "").replace("novo projeto", "").strip()
                if not name:
                    return "Informe o nome do workspace. Ex: 'jarvis, criar workspace MeuProjeto'"
                desc = f"Workspace criado em {datetime.now().strftime('%Y-%m-%d')}"
                ws_id = self.context_builder.workspace_memory.create_workspace(name, desc)
                self.context_builder.workspace_memory.set_active_workspace(name)
                return f"✅ Workspace '{name}' criado e ativado."

            # Ativar workspace
            elif "ativar workspace" in command_lower or "trocar projeto" in command_lower:
                name = command.replace("ativar workspace", "").replace("trocar projeto", "").strip()
                if not name:
                    active = self.context_builder.workspace_memory.get_active_workspace()
                    if active:
                        return f"Workspace ativo: {active.name}"
                    return "Nenhum workspace ativo."
                if self.context_builder.workspace_memory.set_active_workspace(name):
                    return f"✅ Workspace '{name}' ativado."
                return f"Workspace '{name}' não encontrado."

            # Listar workspaces
            elif "listar workspaces" in command_lower:
                workspaces = self.context_builder.workspace_memory.list_workspaces()
                if not workspaces:
                    return "Nenhum workspace criado."
                parts = ["📁 Workspaces:"]
                for ws in workspaces:
                    marker = "✅" if ws.is_active else "  "
                    parts.append(f"  {marker} {ws.name}")
                return "\n".join(parts)

            # Status do workspace
            elif "status workspace" in command_lower or "meu workspace" in command_lower:
                ws = self.context_builder.workspace_memory.get_active_workspace()
                if not ws:
                    return "Nenhum workspace ativo."
                return self.context_builder.workspace_memory.get_workspace_context()

            else:
                return "Comando de workspace não reconhecido."

        except Exception as e:
            return f"Erro ao processar comando de workspace: {e}"

    def _log_to_database(self, command: str, action: str, target: str, result: str, success: bool):
        """Registra dados no Core Database (SQL)."""
        if not self.db:
            return

        try:
            # Log de conversa
            self.db.log_conversation(
                session_id=self.session_id,
                role="user",
                message=command,
                action=action,
                target=target,
                result=result[:200] if result else ""
            )

            # Log de ação executada
            self.db.log_action(
                action=action,
                target=target,
                result=result,
                success=success,
                execution_time_ms=None,
                error=None
            )

            # Registrar uso para estatísticas
            self.db.increment_usage(action, success=success)

            # RL: atualizar scores
            context = self._detect_context(action)
            reward_value = 1.0 if success else -0.5
            self.db.update_rl_stats(action, reward_value, success)
            if context != "general":
                self.db.update_rl_context(context, action, reward_value, success)

            # Log de feedback
            self.db.log_feedback(
                action=action,
                reward_type="correct" if success else "incorrect",
                reward_value=reward_value,
                context=context,
                command=command,
                result=result,
                success=success,
                rating=None
            )

            # Log no workspace ativo
            if self.context_builder:
                self.context_builder.log_action_to_workspace(
                    action=action,
                    description=f"{target}: {result[:100]}" if target else result[:100],
                    details={"success": success, "command": command},
                    session_id=self.session_id
                )

        except Exception as e:
            print(f"[DB] Erro ao registrar: {e}")

    def process_command(self, command: str, skip_safety: bool = False) -> str:
        """
        Processa um comando seguindo o fluxo:
        User → Context → Memory → Workspace → MiniMax → RL → Executor → Feedback → DB
        """
        if not command:
            return "Nenhum comando recebido."

        # Evitar comandos duplicados (debounce de 2 segundos)
        import time
        current_time = time.time()
        with self._command_lock:
            if command == self._last_command and (current_time - self._last_command_time) < 2:
                return "Comando já processado recentemente."
            self._last_command = command
            self._last_command_time = current_time

        # ============================================
        # STEP 1: PRE-PROCESSAMENTO (User → Context)
        # ============================================
        original_command = command

        # Remover wake word
        if command.lower().startswith(WAKE_WORD):
            command = command[len(WAKE_WORD):].strip()
        elif command.lower().startswith(f"oi {WAKE_WORD}"):
            command = command[len(f"oi {WAKE_WORD}"):].strip()

        if not command:
            return "Olá! Como posso ajudar?"

        print(f"[COMANDO] {original_command}")

        # ============================================
        # STEP 1.5: VERIFICAR PERGUNTAS SOBRE O PROJETO
        # ============================================
        if self.context_builder:
            question_lower = command.lower()
            project_keywords = ["onde parei", "onde eu parei", "o que fiz ontem",
                              "problema", "erro recorrente", "última análise",
                              "tarefa", "pendente", "workspace", "projeto atual"]

            if any(kw in question_lower for kw in project_keywords):
                answer = self.context_builder.answer_project_question(command)
                return answer

            # Verificar comandos de workspace
            ws_commands = ["criar workspace", "ativar workspace", "listar workspaces",
                          "novo projeto", "trocar projeto"]
            if any(cmd in question_lower for cmd in ws_commands):
                return self._handle_workspace_command(command)

        # ============================================
        # STEP 2: ANÁLISE MiniMax (Context → MiniMax)
        # ============================================
        decision = analyze_command(command)

        action = decision.get("action", "chat")
        target = decision.get("target", "")
        parameters = decision.get("parameters", {})

        # ============================================
        # STEP 3: VERIFICAR AÇÕES PERIGOSAS (Safety)
        # ============================================
        if not skip_safety and self.safety.requires_confirmation(action):
            confirmation_request = self.safety.request_confirmation(action, target, self.session_id)
            return f"{confirmation_request['message']}\n\nAguardando confirmação..."

        # ============================================
        # STEP 4: EXECUTAR AÇÃO (Executor)
        # ============================================
        # Tentar usar Tool Registry primeiro, depois fallback
        tool = get_tool(action)
        if tool:
            result = execute_tool(action, target, parameters)
        else:
            # Fallback para functions original
            from functions import execute_action
            result = execute_action(action, target, parameters)

        # ============================================
        # STEP 5: AVALIAR RESULTADO (Feedback)
        # ============================================
        success = "erro" not in result.lower()[:20] and "não" not in result.lower()[:10]

        # ============================================
        # STEP 6: REGISTRAR NO BANCO (DB)
        # ============================================
        self._log_to_database(original_command, action, target, result, success)

        # ============================================
        # STEP 7: ATUALIZAR ML LEGACY
        # ============================================
        if ML_AVAILABLE and action not in ["chat", "error"]:
            try:
                add_command(original_command, action)
                record_action(action)
            except Exception:
                pass

        return result

    def run_terminal_mode(self, with_web: bool = True) -> None:
        """Modo terminal com interface web."""
        print("=" * 50)
        print("JARVIS MINIMAX v2.0 - Terminal Mode")
        print("Digite 'sair' para encerrar")
        print("=" * 50)

        if with_web and FLASK_AVAILABLE:
            self.start_web_server()
            print("[WEB] Interface web disponível em http://localhost:5000")
            print()

        self.speak("Jarvis MiniMax ativado. Como posso ajudar?")

        while self.running:
            try:
                command = input("\nVocê: ").strip()

                if not command:
                    continue

                if command.lower() in ("sair", "exit", "quit", "tchau"):
                    print("Jarvis: Até logo!")
                    break

                result = self.process_command(command)
                print(f"\nJarvis: {result}")
                self.speak(result)

            except KeyboardInterrupt:
                print("\n\nJarvis: Interrompido pelo usuário.")
                break
            except Exception as e:
                print(f"\n[ERRO] {e}")

    def run_voice_mode(self) -> None:
        """Modo comandos de voz."""
        if not VOICE_AVAILABLE:
            print("[ERRO] Modo voz não disponível.")
            return

        print("=" * 50)
        print("JARVIS MINIMAX v2.0 - Voice Mode")
        print(f"Diga '{WAKE_WORD}' para ativar")
        print("Ctrl+C para encerrar")
        print("=" * 50)

        self.speak("Jarvis MiniMax ativado.")

        while self.running:
            try:
                command = self.listen()
                if command:
                    result = self.process_command(command)
                    self.speak(result)
            except KeyboardInterrupt:
                print("\n\nJarvis: Encerrando...")
                break
            except Exception as e:
                print(f"\n[ERRO] {e}")
                self.speak("Ocorreu um erro.")

    def run_api_mode(self, port: int = 8765) -> None:
        """Modo API HTTP."""
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler
        except ImportError:
            print("[ERRO] Modo API não disponível.")
            return

        class JarvisAPIHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path == "/command":
                    content_length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(content_length).decode("utf-8")

                    try:
                        data = json.loads(body)
                        command = data.get("command", "")
                        result = self.server.jarvis.process_command(command)

                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"result": result}).encode())
                    except Exception as e:
                        self.send_response(500)
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": str(e)}).encode())
                elif self.path == "/confirm":
                    content_length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(content_length).decode("utf-8")
                    data = json.loads(body)
                    confirmation_id = data.get("confirmation_id")
                    user_response = data.get("response", "")
                    result = self.server.jarvis.safety.check_confirmation(confirmation_id, user_response)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(result).encode())

            def log_message(self, format, *args):
                print(f"[API] {format % args}")

        class JarvisHTTPServer(HTTPServer):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.jarvis = self

        print(f"[API] Iniciando servidor na porta {port}...")
        server = JarvisHTTPServer(("0.0.0.0", port), JarvisAPIHandler)
        print(f"[API] Jarvis API rodando em http://0.0.0.0:{port}")
        print("[API] POST /command | POST /confirm")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[API] Servidor encerrado.")
            server.shutdown()


def main():
    print("=" * 50)
    print("  JARVIS MINIMAX v2.0")
    print("  Arquitetura Refatorada")
    print("=" * 50)
    print()

    from config.settings import MINIMAX_API_KEY
    if not MINIMAX_API_KEY:
        print("[ERRO] MINIMAX_API_KEY não configurada!")
        print("Edite o arquivo .env na raiz do projeto.")
        sys.exit(1)

    jarvis = JarvisMiniMax()

    # Status
    print(f"[INICIALIZAÇÃO] Session ID: {jarvis.session_id}")
    print(f"[INICIALIZAÇÃO] Tools carregados: {len(jarvis.tool_registry.list_all())}")
    print(f"[INICIALIZAÇÃO] Database: {'OK' if DB_AVAILABLE else 'INDISPONÍVEL'}")
    print(f"[INICIALIZAÇÃO] RL System: {'OK' if RL_AVAILABLE else 'INDISPONÍVEL'}")
    print()

    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()

        if mode == "--voice" or mode == "-v":
            jarvis.run_voice_mode()
        elif mode == "--api" or mode == "-a":
            port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
            jarvis.run_api_mode(port)
        elif mode == "--web" or mode == "-w":
            if not FLASK_AVAILABLE:
                print("[ERRO] Flask não disponível. Instale com: pip install flask")
                sys.exit(1)
            print("Iniciando Jarvis Web...")
            jarvis.start_web_server()
            print("Pressione Ctrl+C para encerrar")
            try:
                while jarvis.running:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nEncerrando...")
        elif mode == "--help" or mode == "-h":
            print("Uso: python3 main.py [opção]")
            print()
            print("Opções:")
            print("  (nada)     - Modo terminal + web (unificado)")
            print("  --web      - Apenas modo web")
            print("  --voice    - Modo voz")
            print("  --api [port] - Modo API")
            print("  --help     - Esta ajuda")
        else:
            print(f"Opção desconhecida: {mode}")
    else:
        jarvis.run_terminal_mode(with_web=True)


if __name__ == "__main__":
    main()