#!/usr/bin/env python3
"""
Jarvis MiniMax - Assistente de automação com IA da MiniMax
"""

import sys
import json
import threading

# Tentar importar componentes opcionais
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

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


from core.minimax_client import analyze_command
from functions import execute_action
from config.settings import WAKE_WORD


class JarvisMiniMax:
    def __init__(self):
        self.running = True
        self.tts_engine = None
        self.web_server = None
        self.web_thread = None

        if TTS_AVAILABLE:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty("rate", 160)
                voices = self.tts_engine.getProperty("voices")
                if voices:
                    self.tts_engine.setProperty("voice", voices[0].id)
            except Exception:
                self.tts_engine = None

        self.recognizer = None
        self.microphone = None

        if VOICE_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                self.microphone = sr.Microphone()
            except Exception:
                self.recognizer = None
                self.microphone = None

        # Setup Flask web app
        self.app = None
        self._setup_web_app()

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

                decision = analyze_command(command)
                action = decision.get("action", "chat")
                target = decision.get("target", "")
                parameters = decision.get("parameters", {})
                result = execute_action(action, target, parameters)

                return jsonify({
                    "success": True,
                    "action": action,
                    "target": target,
                    "result": result
                })
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

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
        print(f"[JARVIS] {text}")
        if self.tts_engine:
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception:
                pass

    def listen(self) -> str | None:
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

    def process_command(self, command: str) -> str:
        if not command:
            return "Nenhum comando recebido."

        if command.lower().startswith(WAKE_WORD):
            command = command[len(WAKE_WORD):].strip()
        elif command.lower().startswith(f"oi {WAKE_WORD}"):
            command = command[len(f"oi {WAKE_WORD}"):].strip()

        if not command:
            return "Olá! Como posso ajudar?"

        print(f"[COMANDO] {command}")
        print("[MINIMAX] Analisando comando...")

        decision = analyze_command(command)

        action = decision.get("action", "chat")
        target = decision.get("target", "")
        parameters = decision.get("parameters", {})

        print(f"[DECISÃO] action={action}, target={target}")

        result = execute_action(action, target, parameters)

        return result

    def run_terminal_mode(self, with_web: bool = True) -> None:
        print("=" * 50)
        print("JARVIS MINIMAX - Terminal Mode")
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
        if not VOICE_AVAILABLE:
            print("[ERRO] Modo voz não disponível.")
            return

        print("=" * 50)
        print("JARVIS MINIMAX - Voice Mode")
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
        """Modo API - servidor HTTP."""
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
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                print(f"[API] {format % args}")

        class JarvisHTTPServer(HTTPServer):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.jarvis = self

        print(f"[API] Iniciando servidor na porta {port}...")
        server = JarvisHTTPServer(("0.0.0.0", port), JarvisAPIHandler)
        print(f"[API] Jarvis API rodando em http://0.0.0.0:{port}")
        print("[API] POST /command")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[API] Servidor encerrado.")
            server.shutdown()


def main():
    print("=" * 50)
    print("  JARVIS MINIMAX")
    print("  Assistente com IA da MiniMax")
    print("=" * 50)
    print()

    from config.settings import MINIMAX_API_KEY
    if not MINIMAX_API_KEY:
        print("[ERRO] MINIMAX_API_KEY não configurada!")
        print("Edite o arquivo .env na raiz do projeto.")
        sys.exit(1)

    jarvis = JarvisMiniMax()

    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()

        if mode == "--voice" or mode == "-v":
            jarvis.run_voice_mode()
        elif mode == "--api" or mode == "-a":
            port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
            jarvis.run_api_mode(port)
        elif mode == "--web" or mode == "-w":
            # Apenas modo web (sem terminal)
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
        # Modo padrão: terminal + web juntos
        jarvis.run_terminal_mode(with_web=True)


if __name__ == "__main__":
    main()