"""
Funções de automação do Jarvis MiniMax
"""

import os
import sys
import subprocess
import webbrowser
import shutil
import time
import json
import re
import threading
from pathlib import Path
from datetime import datetime, timedelta

# Tentar importar pyautogui
PYAUTOGUI_AVAILABLE = False
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    PYAUTOGUI_AVAILABLE = True
except Exception:
    pass


# ========================
# SISTEMA
# ========================

def search_web(query: str) -> str:
    if not query:
        return "Informe o que deseja pesquisar."
    try:
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        webbrowser.open(url)
        return f"Pesquisando: {query}"
    except Exception as e:
        return f"Erro ao pesquisar: {e}"


def open_app(app_name: str) -> str:
    if not app_name:
        return "Informe o nome do aplicativo."

    # Mapeamento de nomes comuns para comandos corretos no Linux
    app_mapping = {
        "whatsapp": "whatsapp-desktop",
        "chrome": "google-chrome",
        "code": "code",
        "vscode": "code",
        "terminal": "gnome-terminal",
        "arquivos": "nautilus",
        "arquivo": "nautilus",
        "files": "nautilus",
        "spotify": "spotify",
        "discord": "discord",
        "telegram": "telegram-desktop",
        "zoom": "zoom",
        "slack": "slack",
        "firefox": "firefox",
        "edge": "msedge",
    }

    app_lower = app_name.lower().strip()
    command = app_mapping.get(app_lower, app_lower)

    try:
        if sys.platform == "linux":
            # Primeiro tenta o nome mapeado
            result = subprocess.run(["which", command], capture_output=True, text=True)
            if result.returncode != 0:
                # Se não encontrou, tenta o nome original
                result = subprocess.run(["which", app_name.lower()], capture_output=True, text=True)
                if result.returncode == 0:
                    command = app_name.lower()

            subprocess.Popen([command])
            return f"Abrindo {app_name}"
        else:
            subprocess.Popen([app_name])
            return f"Abrindo {app_name}"
    except Exception as e:
        return f"Erro ao abrir {app_name}: {e}"


def open_site(url: str) -> str:
    if not url:
        return "Informe a URL."
    if not url.startswith("http"):
        url = "https://" + url
    try:
        webbrowser.open(url)
        return f"Abrindo: {url}"
    except Exception as e:
        return f"Erro ao abrir site: {e}"


def close_app(app_name: str) -> str:
    if not app_name:
        return "Informe o nome do aplicativo."

    # Mapeamento de nomes comuns para nomes de processos
    process_mapping = {
        "whatsapp": "whatsapp-desktop",
        "chrome": "chrome",
        "google chrome": "chrome",
        "code": "code",
        "vscode": "code",
        "terminal": "gnome-terminal",
        "arquivos": "nautilus",
        "files": "nautilus",
        "spotify": "spotify",
        "discord": "discord",
        "telegram": "telegram-desktop",
        "zoom": "zoom",
        "slack": "slack",
        "firefox": "firefox",
        "edge": "msedge",
        "opera": "opera",
        "brave": "brave-browser",
    }

    app_lower = app_name.lower().strip()
    process_name = process_mapping.get(app_lower, app_lower)

    try:
        if sys.platform == "linux":
            # Primeiro tenta killall
            result = subprocess.run(
                ["killall", "-9", process_name],
                capture_output=True, timeout=5
            )
            if result.returncode != 0:
                # Tenta com o nome original
                result = subprocess.run(
                    ["killall", "-9", app_lower],
                    capture_output=True, timeout=5
                )
        elif sys.platform == "win32":
            os.system(f"taskkill /IM {process_name}.exe /F")
        return f"Fechando {app_name}"
    except Exception as e:
        return f"Erro ao fechar {app_name}: {e}"


def shutdown_pc() -> str:
    try:
        if sys.platform == "linux":
            subprocess.Popen(["shutdown", "-h", "now"])
        elif sys.platform == "win32":
            subprocess.Popen(["shutdown", "/s", "/t", "0"])
        return "Desligando PC..."
    except Exception as e:
        return f"Erro ao desligar PC: {e}"


def schedule_shutdown(minutes: str) -> str:
    """Agenda o desligamento do PC após X minutos."""
    if not minutes:
        return "Informe quantos minutos para desligar"
    try:
        delay = int(minutes)
        if delay <= 0:
            return "Informe um número positivo de minutos"

        seconds = delay * 60

        # Cancelar shutdown anterior
        if sys.platform == "linux":
            subprocess.run(["shutdown", "-c"], capture_output=True)
        elif sys.platform == "win32":
            subprocess.Popen(["shutdown", "/a"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Agendar novo shutdown em uma thread separada
        def delayed_shutdown():
            time.sleep(seconds)
            if sys.platform == "linux":
                subprocess.Popen(["shutdown", "-h", "now"])
            elif sys.platform == "win32":
                subprocess.Popen(["shutdown", "/s", "/t", "0"])

        thread = threading.Thread(target=delayed_shutdown, daemon=True)
        thread.start()

        return f"PC agendado para desligar em {minutes} minutos"
    except Exception as e:
        return f"Erro ao agendar desligamento: {e}"


def cancel_shutdown() -> str:
    """Cancela o desligamento agendado."""
    try:
        if sys.platform == "linux":
            result = subprocess.run(["shutdown", "-c"], capture_output=True, text=True)
            if result.returncode == 0:
                return "Desligamento cancelado"
            return "Nenhum desligamento agendado"
        elif sys.platform == "win32":
            subprocess.Popen(["shutdown", "/a"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "Desligamento cancelado"
    except Exception as e:
        return f"Erro ao cancelar: {e}"


# ========================
# AGENDAMENTO DE DEPLOY
# ========================

_deploy_schedules = {}
_deploy_lock = threading.Lock()


def _execute_scheduled_deploy(schedule_id: str, recurring: bool):
    """Executa o deploy agendado."""
    try:
        result = deploy()
        print(f"[DEPLOY AGENDADO] {schedule_id}: {result[:100]}")
    except Exception as e:
        print(f"[DEPLOY AGENDADO] Erro: {e}")

    if recurring:
        with _deploy_lock:
            if schedule_id in _deploy_schedules:
                _deploy_schedules[schedule_id].cancel()
                del _deploy_schedules[schedule_id]


def schedule_deploy(time_str: str, recurring: str = "") -> str:
    """
    Agenda um deploy para uma hora específica.
    Uso: schedule_deploy "14:30" ou schedule_deploy "14"
    recurring: "diario", "todos os dias" para recurência diária
    """
    import re

    if not time_str:
        return "Informe a hora do deploy. Ex: 14:30 ou 14"

    time_str = time_str.strip()
    recurring_lower = recurring.lower() if recurring else ""

    match = re.match(r'(\d{1,2})(?::(\d{2}))?', time_str)
    if not match:
        return "Formato de hora inválido. Use HH:MM ou HH."

    hour = int(match.group(1))
    minute = int(match.group(2) or "0")

    if hour > 23 or minute > 59:
        return "Hora inválida."

    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if target <= now:
        target = target + timedelta(days=1)

    seconds = (target - now).total_seconds()

    schedule_id = f"{hour:02d}:{minute:02d}"
    is_recurring = "diario" in recurring_lower or "todos" in recurring_lower
    if is_recurring:
        schedule_id += "_daily"

    with _deploy_lock:
        if schedule_id in _deploy_schedules:
            _deploy_schedules[schedule_id].cancel()

        timer = threading.Timer(seconds, _execute_scheduled_deploy, args=[schedule_id, is_recurring])
        timer.daemon = True
        _deploy_schedules[schedule_id] = timer
        timer.start()

    recurrence_text = " (diário)" if is_recurring else ""
    return f"🚀 Deploy agendado para {hour:02d}:{minute:02d}{recurrence_text}"


def cancel_deploy_schedule(time_str: str = "") -> str:
    """Cancela um deploy agendado."""
    import re

    with _deploy_lock:
        if not time_str:
            for sid, timer in list(_deploy_schedules.items()):
                timer.cancel()
            _deploy_schedules.clear()
            return "Todos os deploys agendados cancelados."

        match = re.match(r'(\d{1,2})(?::(\d{2}))?', time_str.strip())
        if not match:
            return "Formato de hora inválido."

        hour = int(match.group(1))
        minute = int(match.group(2) or "0")
        schedule_id = f"{hour:02d}:{minute:02d}"

        removed = False
        for suffix in ["", "_daily"]:
            sid = schedule_id + suffix
            if sid in _deploy_schedules:
                _deploy_schedules[sid].cancel()
                del _deploy_schedules[sid]
                removed = True

        if removed:
            return f"Deploy das {hour:02d}:{minute:02d} cancelado."
        return f"Nenhum deploy encontrado para {hour:02d}:{minute:02d}."


def list_deploy_schedules() -> str:
    """Lista todos os deploys agendados."""
    with _deploy_lock:
        if not _deploy_schedules:
            return "Nenhum deploy agendado."

        lines = ["🚀 Deploys agendados:"]
        for sid in sorted(_deploy_schedules.keys()):
            suffix = " (diário)" if sid.endswith("_daily") else ""
            time_part = sid.replace("_daily", "")
            lines.append(f"  - {time_part}{suffix}")

        return "\n".join(lines)


def restart_pc() -> str:
    try:
        if sys.platform == "linux":
            subprocess.Popen(["shutdown", "-r", "now"])
        elif sys.platform == "win32":
            subprocess.Popen(["shutdown", "/r", "/t", "0"])
        return "Reiniciando PC..."
    except Exception as e:
        return f"Erro ao reiniciar PC: {e}"


def hibernate_pc() -> str:
    try:
        if sys.platform == "linux":
            subprocess.Popen(["systemctl", "hibernate"])
        elif sys.platform == "win32":
            subprocess.Popen(["shutdown", "/h"])
        return "PC em hibernação"
    except Exception as e:
        return f"Erro ao hibernar: {e}"


def sleep_mode() -> str:
    try:
        if sys.platform == "linux":
            subprocess.Popen(["systemctl", "suspend"])
        elif sys.platform == "win32":
            subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"])
        return "PC em modo de suspensão"
    except Exception as e:
        return f"Erro ao suspender: {e}"


def wifi_on() -> str:
    try:
        if sys.platform == "linux":
            subprocess.Popen(["nmcli", "radio", "wifi", "on"])
        return "WiFi ligado"
    except Exception as e:
        return f"Erro ao ligar WiFi: {e}"


def wifi_off() -> str:
    try:
        if sys.platform == "linux":
            subprocess.Popen(["nmcli", "radio", "wifi", "off"])
        return "WiFi desligado"
    except Exception as e:
        return f"Erro ao desligar WiFi: {e}"


def set_brightness(level: str) -> str:
    if not level:
        return "Informe o nível de brilho (0-100)"
    try:
        if sys.platform == "linux":
            subprocess.Popen(["brightnessctl", "set", f"{level}%"])
        return f"Brilho definido para {level}%"
    except Exception as e:
        return f"Erro ao definir brilho: {e}"


# ========================
# VOLUME E MÍDIA
# ========================

def volume_up() -> str:
    try:
        if sys.platform == "linux":
            subprocess.Popen(["amixer", "-D", "pulse", "sset", "Master", "5%+"])
        elif sys.platform == "win32":
            subprocess.Popen(["nircmd", "volup", "5000"])
        return "Volume aumentado"
    except Exception as e:
        return f"Erro: {e}"


def volume_down() -> str:
    try:
        if sys.platform == "linux":
            subprocess.Popen(["amixer", "-D", "pulse", "sset", "Master", "5%-"])
        elif sys.platform == "win32":
            subprocess.Popen(["nircmd", "voldown", "5000"])
        return "Volume diminuído"
    except Exception as e:
        return f"Erro: {e}"


def mute() -> str:
    try:
        if sys.platform == "linux":
            subprocess.Popen(["amixer", "-D", "pulse", "sset", "Master", "toggle"])
        elif sys.platform == "win32":
            subprocess.Popen(["nircmd", "mutesysvolume", "2"])
        return "Som mutado"
    except Exception as e:
        return f"Erro: {e}"


def spotify_play() -> str:
    try:
        if sys.platform == "linux":
            subprocess.Popen(["dbus-send", "--print-reply", "--dest=org.mpris.MediaPlayer2.spotify",
                           "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player.Play"])
        return "Spotify tocando"
    except Exception as e:
        return f"Erro: {e}"


def spotify_pause() -> str:
    try:
        if sys.platform == "linux":
            subprocess.Popen(["dbus-send", "--print-reply", "--dest=org.mpris.MediaPlayer2.spotify",
                           "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player.Pause"])
        return "Spotify pausado"
    except Exception as e:
        return f"Erro: {e}"


def spotify_next() -> str:
    try:
        if sys.platform == "linux":
            subprocess.Popen(["dbus-send", "--print-reply", "--dest=org.mpris.MediaPlayer2.spotify",
                           "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player.Next"])
        return "Próxima música"
    except Exception as e:
        return f"Erro: {e}"


def spotify_previous() -> str:
    try:
        if sys.platform == "linux":
            subprocess.Popen(["dbus-send", "--print-reply", "--dest=org.mpris.MediaPlayer2.spotify",
                           "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player.Previous"])
        return "Música anterior"
    except Exception as e:
        return f"Erro: {e}"


# ========================
# ARQUIVOS
# ========================

def open_folder(path: str) -> str:
    if not path:
        return "Informe o caminho da pasta."
    try:
        path_obj = Path(path)
        if not path_obj.exists():
            return f"Caminho não existe: {path}"
        if sys.platform == "linux":
            subprocess.Popen(["xdg-open", str(path)])
        elif sys.platform == "win32":
            os.startfile(str(path))
        return f"Abrindo pasta: {path}"
    except Exception as e:
        return f"Erro ao abrir pasta: {e}"


def create_file(filename: str, content: str = "") -> str:
    if not filename:
        return "Informe o nome do arquivo."
    try:
        from config.settings import BASE_DIR
        if "/" not in filename and "\\" not in filename:
            filepath = BASE_DIR / filename
        else:
            filepath = Path(filename)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content or "", encoding="utf-8")
        return f"Arquivo criado: {filepath}"
    except Exception as e:
        return f"Erro ao criar arquivo: {e}"


def read_file(path: str) -> str:
    if not path:
        return "Informe o caminho do arquivo."
    try:
        filepath = Path(path)
        if not filepath.exists():
            return f"Arquivo não encontrado: {path}"
        content = filepath.read_text(encoding="utf-8")
        if len(content) > 1000:
            content = content[:1000] + "\n... (arquivo truncado)"
        return f"Conteúdo de {path}:\n\n{content}"
    except Exception as e:
        return f"Erro ao ler arquivo: {e}"


def delete_file(path: str) -> str:
    if not path:
        return "Informe o caminho do arquivo."
    try:
        filepath = Path(path)
        if not filepath.exists():
            return f"Arquivo não encontrado: {path}"
        filepath.unlink()
        return f"Arquivo deletado: {path}"
    except Exception as e:
        return f"Erro ao deletar arquivo: {e}"


def rename_file(old_path: str, new_name: str) -> str:
    if not old_path or not new_name:
        return "Informe o caminho atual e o novo nome."
    try:
        filepath = Path(old_path)
        if not filepath.exists():
            return f"Arquivo não encontrado: {old_path}"
        new_path = filepath.parent / new_name
        filepath.rename(new_path)
        return f"Arquivo renomeado para: {new_path}"
    except Exception as e:
        return f"Erro ao renomear arquivo: {e}"


def move_file(source: str, destination: str) -> str:
    if not source or not destination:
        return "Informe o caminho de origem e destino."
    try:
        src = Path(source)
        dst = Path(destination)
        if not src.exists():
            return f"Arquivo de origem não encontrado: {source}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return f"Arquivo movido para: {dst}"
    except Exception as e:
        return f"Erro ao mover arquivo: {e}"


def copy_file(source: str, destination: str) -> str:
    if not source or not destination:
        return "Informe o caminho de origem e destino."
    try:
        src = Path(source)
        dst = Path(destination)
        if not src.exists():
            return f"Arquivo de origem não encontrado: {source}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
        return f"Arquivo copiado para: {dst}"
    except Exception as e:
        return f"Erro ao copiar arquivo: {e}"


def organize_folder(path: str) -> str:
    if not path:
        return "Informe o caminho da pasta."
    try:
        folder = Path(path)
        if not folder.exists():
            return f"Pasta não encontrada: {path}"
        extensions = {}
        for file in folder.iterdir():
            if file.is_file():
                ext = file.suffix.lower() or "sem_extensao"
                if ext not in extensions:
                    extensions[ext] = folder / ext[1:]
                    extensions[ext].mkdir(exist_ok=True)
                shutil.move(str(file), str(extensions[ext] / file.name))
        return f"Pasta organizada: {path}"
    except Exception as e:
        return f"Erro ao organizar pasta: {e}"


def find_file(name: str) -> str:
    if not name:
        return "Informe o nome do arquivo."
    try:
        from config.settings import BASE_DIR
        results = []
        for f in BASE_DIR.rglob(f"*{name}*"):
            results.append(str(f))
        if not results:
            return f"Arquivo '{name}' não encontrado"
        return f"Arquivos encontrados:\n" + "\n".join(results[:10])
    except Exception as e:
        return f"Erro ao buscar arquivo: {e}"


# ========================
# GIT
# ========================

def git_status() -> str:
    try:
        from config.settings import BASE_DIR
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=BASE_DIR)
        if not result.stdout.strip():
            return "Repositório limpo - nada para commitar"
        return f"Status git:\n{result.stdout}"
    except Exception as e:
        return f"Erro: {e}"


def git_log(limit: str = "10") -> str:
    try:
        from config.settings import BASE_DIR
        result = subprocess.run(["git", "log", f"--oneline", "-n", str(limit or "10")],
                             capture_output=True, text=True, cwd=BASE_DIR)
        return result.stdout or "Sem commits"
    except Exception as e:
        return f"Erro: {e}"


def git_pull() -> str:
    try:
        from config.settings import BASE_DIR
        result = subprocess.run(["git", "pull"], capture_output=True, text=True, cwd=BASE_DIR)
        return result.stdout or "Pull realizado"
    except Exception as e:
        return f"Erro: {e}"


def git_push() -> str:
    try:
        from config.settings import BASE_DIR
        result = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=BASE_DIR)
        return result.stdout or "Push realizado"
    except Exception as e:
        return f"Erro: {e}"


def git_commit(message: str) -> str:
    if not message:
        return "Informe a mensagem do commit"
    try:
        from config.settings import BASE_DIR
        subprocess.run(["git", "add", "."], cwd=BASE_DIR)
        result = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True, cwd=BASE_DIR)
        return result.stdout or "Commit realizado"
    except Exception as e:
        return f"Erro: {e}"


# ========================
# MONITORAMENTO DO PC
# ========================

def hardware_status() -> str:
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return (f"CPU: {cpu}%\nMemória: {mem.percent}%\nDisco: {disk.percent}%")
    except ImportError:
        return "Instale psutil para status do hardware"
    except Exception as e:
        return f"Erro: {e}"


def disk_health() -> str:
    try:
        import psutil
        partitions = psutil.disk_partitions()
        result = []
        for p in partitions:
            try:
                usage = psutil.disk_usage(p.mountpoint)
                result.append(f"{p.device}: {usage.used//(1024**3)}GB / {usage.total//(1024**3)}GB")
            except:
                pass
        return "\n".join(result) if result else "Nenhum disco encontrado"
    except ImportError:
        return "Instale psutil para status do disco"
    except Exception as e:
        return f"Erro: {e}"


def internet_speed() -> str:
    try:
        import speedtest
        s = speedtest.Speedtest()
        s.download()
        s.upload()
        return f"Download: {s.download() / 1024 / 1024:.2f} Mbps\nUpload: {s.upload() / 1024 / 1024:.2f} Mbps"
    except ImportError:
        return "Instale speedtest-cli para testar velocidade"
    except Exception as e:
        return f"Erro: {e}"


# ========================
# SCREENSHOT E TECLADO
# ========================

def screenshot() -> str:
    if not PYAUTOGUI_AVAILABLE:
        return "pyautogui não disponível"
    try:
        from config.settings import DATA_DIR
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = DATA_DIR / filename
        img = pyautogui.screenshot()
        img.save(str(filepath))
        return f"Screenshot salvo em: {filepath}"
    except Exception as e:
        return f"Erro ao tirar screenshot: {e}"


def type_text(text: str) -> str:
    if not text:
        return "Informe o texto a digitar."
    if not PYAUTOGUI_AVAILABLE:
        return "pyautogui não disponível"
    try:
        pyautogui.write(text, interval=0.05)
        return f"Digitado: {text}"
    except Exception as e:
        return f"Erro ao digitar: {e}"


def press_key(keys: str) -> str:
    if not keys:
        return "Informe a tecla."
    if not PYAUTOGUI_AVAILABLE:
        return "pyautogui não disponível"
    try:
        keys = keys.lower().strip()
        key_map = {"enter": "enter", "tab": "tab", "esc": "escape", "space": "space", "backspace": "backspace"}
        if "+" in keys:
            parts = keys.split("+")
            pyautogui.hotkey(*parts)
        else:
            pyautogui.press(key_map.get(keys, keys))
        return f"Tecla pressionada: {keys}"
    except Exception as e:
        return f"Erro ao pressionar tecla: {e}"


def click_mouse() -> str:
    if not PYAUTOGUI_AVAILABLE:
        return "pyautogui não disponível"
    try:
        pyautogui.click()
        return "Clique realizado"
    except Exception as e:
        return f"Erro: {e}"


def move_mouse(x: str, y: str) -> str:
    if not x or not y:
        return "Informe as coordenadas X e Y"
    if not PYAUTOGUI_AVAILABLE:
        return "pyautogui não disponível"
    try:
        pyautogui.moveTo(int(x), int(y))
        return f"Mouse movido para ({x}, {y})"
    except Exception as e:
        return f"Erro: {e}"


def hotkey(*keys) -> str:
    if not keys:
        return "Informe as teclas para o atalho"
    if not PYAUTOGUI_AVAILABLE:
        return "pyautogui não disponível"
    try:
        pyautogui.hotkey(*keys)
        return f"Atalho executado: {'+'.join(keys)}"
    except Exception as e:
        return f"Erro: {e}"


# ========================
# DESPERTADOR / ALARME
# ========================

import threading
import subprocess
from pathlib import Path

# Armazena os timers dos alarmes
_active_alarms = {}
_alarm_lock = threading.Lock()

ALARM_SOUND_FILE = str(Path(__file__).parent.parent / "re0r.mp3")


def _play_alarm():
    """Toca o som do alarme até ser parado."""
    subprocess.Popen(["paplay", ALARM_SOUND_FILE],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def set_alarm(time_str: str, recurring: str = "") -> str:
    """
    Define um alarme para despertar.
    Uso: set_alarm "14:30" ou set_alarm "14" (horas)
    recurring: "diario", "todos os dias", semanal", etc.
    """
    import re

    if not time_str:
        return "Informe a hora do alarme. Ex: 14:30 ou 14"

    # Parse da hora
    time_str = time_str.strip()
    recurring_lower = recurring.lower() if recurring else ""

    # Extrair hora e minuto
    match = re.match(r'(\d{1,2})(?::(\d{2}))?', time_str)
    if not match:
        return "Formato de hora inválido. Use HH:MM ou HH."

    hour = int(match.group(1))
    minute = int(match.group(2) or "0")

    if hour > 23 or minute > 59:
        return "Hora inválida."

    # Calcular segundos até o alarme
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # Se já passou hoje, agendar para amanhã
    if target <= now:
        target = target + timedelta(days=1)

    seconds = (target - now).total_seconds()

    alarm_id = f"{hour:02d}:{minute:02d}"
    if "diario" in recurring_lower or "todos" in recurring_lower:
        alarm_id += "_daily"

    with _alarm_lock:
        # Cancelar alarme existente com mesmo ID
        if alarm_id in _active_alarms:
            _active_alarms[alarm_id].cancel()

        # Criar timer
        timer = threading.Timer(seconds, _trigger_alarm, args=[alarm_id, "diario" in recurring_lower])
        timer.daemon = True
        _active_alarms[alarm_id] = timer
        timer.start()

    recurrence_text = " (diário)" if "diario" in recurring_lower else ""
    return f"⏰ Alarme definido para {hour:02d}:{minute:02d}{recurrence_text}"


def _trigger_alarm(alarm_id: str, recurring: bool):
    """Dispara o alarme."""
    _play_alarm()

    # Se é recorrente, reprogramar
    if recurring:
        with _alarm_lock:
            if alarm_id in _active_alarms:
                _active_alarms[alarm_id].cancel()

        # Reprogramar para o dia seguinte
        timer = threading.Timer(86400, _trigger_alarm, args=[alarm_id, True])
        timer.daemon = True
        with _alarm_lock:
            _active_alarms[alarm_id] = timer
        timer.start()


def cancel_alarm(time_str: str = "") -> str:
    """
    Cancela um alarme específico ou todos.
    Uso: cancel_alarm "14:30" ou cancel_alarm (todos)
    """
    import re

    with _alarm_lock:
        if not time_str:
            # Cancelar todos
            for alarm_id, timer in list(_active_alarms.items()):
                timer.cancel()
            _active_alarms.clear()
            return "Todos os alarmes cancelados."

        # Parse da hora
        match = re.match(r'(\d{1,2})(?::(\d{2}))?', time_str.strip())
        if not match:
            return "Formato de hora inválido."

        hour = int(match.group(1))
        minute = int(match.group(2) or "0")
        alarm_id = f"{hour:02d}:{minute:02d}"

        # Tentar cancelar tanto simples quanto diário
        removed = False
        for suffix in ["", "_daily"]:
            aid = alarm_id + suffix
            if aid in _active_alarms:
                _active_alarms[aid].cancel()
                del _active_alarms[aid]
                removed = True

        if removed:
            return f"Alarme das {hour:02d}:{minute:02d} cancelado."
        return f"Nenhum alarme encontrado para {hour:02d}:{minute:02d}."


def list_alarms() -> str:
    """Lista todos os alarmes ativos."""
    with _alarm_lock:
        if not _active_alarms:
            return "Nenhum alarme ativo."

        lines = ["⏰ Alarmes ativos:"]
        for alarm_id in sorted(_active_alarms.keys()):
            suffix = " (diário)" if alarm_id.endswith("_daily") else ""
            time_part = alarm_id.replace("_daily", "")
            lines.append(f"  - {time_part}{suffix}")

        return "\n".join(lines)


def play_alarm_sound() -> str:
    """Toca o som do alarme uma vez."""
    try:
        _play_alarm()
        return f"🔊 Tocando alarme: {ALARM_SOUND_FILE}"
    except Exception as e:
        return f"Erro ao tocar alarme: {e}"


# ========================
# LEMBRETES E TAREFAS
# ========================

def add_reminder(text: str) -> str:
    if not text:
        return "Informe o lembrete"
    try:
        from config.settings import DATA_DIR
        reminders_file = DATA_DIR / "reminders.json"
        reminders = []
        if reminders_file.exists():
            reminders = json.loads(reminders_file.read_text())
        reminders.append({"text": text, "created": datetime.now().isoformat()})
        reminders_file.write_text(json.dumps(reminders, indent=2))
        return f"Lembrete adicionado: {text}"
    except Exception as e:
        return f"Erro: {e}"


def list_reminders() -> str:
    try:
        from config.settings import DATA_DIR
        reminders_file = DATA_DIR / "reminders.json"
        if not reminders_file.exists():
            return "Nenhum lembrete cadastrado"
        reminders = json.loads(reminders_file.read_text())
        if not reminders:
            return "Nenhum lembrete cadastrado"
        return "Lembretes:\n" + "\n".join(f"- {r['text']}" for r in reminders)
    except Exception as e:
        return f"Erro: {e}"


def add_task(text: str) -> str:
    if not text:
        return "Informe a tarefa"
    try:
        from config.settings import DATA_DIR
        tasks_file = DATA_DIR / "tasks.json"
        tasks = []
        if tasks_file.exists():
            tasks = json.loads(tasks_file.read_text())
        tasks.append({"text": text, "created": datetime.now().isoformat(), "done": False})
        tasks_file.write_text(json.dumps(tasks, indent=2))
        return f"Tarefa adicionada: {text}"
    except Exception as e:
        return f"Erro: {e}"


def list_tasks() -> str:
    try:
        from config.settings import DATA_DIR
        tasks_file = DATA_DIR / "tasks.json"
        if not tasks_file.exists():
            return "Nenhuma tarefa cadastrada"
        tasks = json.loads(tasks_file.read_text())
        if not tasks:
            return "Nenhuma tarefa cadastrada"
        lines = []
        for i, t in enumerate(tasks, 1):
            status = "[x]" if t.get("done") else "[ ]"
            lines.append(f"{i}. {status} {t['text']}")
        return "Tarefas:\n" + "\n".join(lines)
    except Exception as e:
        return f"Erro: {e}"


# ========================
# DESPESAS
# ========================

def add_expense(amount: str, description: str) -> str:
    if not amount:
        return "Informe o valor da despesa"
    try:
        from config.settings import DATA_DIR
        expenses_file = DATA_DIR / "expenses.json"
        expenses = []
        if expenses_file.exists():
            expenses = json.loads(expenses_file.read_text())
        expenses.append({"amount": amount, "description": description or "", "date": datetime.now().isoformat()})
        expenses_file.write_text(json.dumps(expenses, indent=2))
        return f"Despesa adicionada: R$ {amount} - {description}"
    except Exception as e:
        return f"Erro: {e}"


def expense_summary() -> str:
    try:
        from config.settings import DATA_DIR
        expenses_file = DATA_DIR / "expenses.json"
        if not expenses_file.exists():
            return "Nenhuma despesa cadastrada"
        expenses = json.loads(expenses_file.read_text())
        if not expenses:
            return "Nenhuma despesa cadastrada"
        total = sum(float(e.get("amount", 0)) for e in expenses)
        return f"Total de despesas: R$ {total:.2f}\n({len(expenses)} registros)"
    except Exception as e:
        return f"Erro: {e}"


# ========================
# AGENDA
# ========================

def add_event(title: str, date: str = "") -> str:
    if not title:
        return "Informe o título do evento"
    try:
        from config.settings import DATA_DIR
        events_file = DATA_DIR / "events.json"
        events = []
        if events_file.exists():
            events = json.loads(events_file.read_text())
        events.append({"title": title, "date": date or datetime.now().strftime("%Y-%m-%d"), "created": datetime.now().isoformat()})
        events_file.write_text(json.dumps(events, indent=2))
        return f"Evento adicionado: {title}"
    except Exception as e:
        return f"Erro: {e}"


def calendar_today() -> str:
    try:
        from config.settings import DATA_DIR
        events_file = DATA_DIR / "events.json"
        if not events_file.exists():
            return "Nenhum evento para hoje"
        events = json.loads(events_file.read_text())
        today = datetime.now().strftime("%Y-%m-%d")
        today_events = [e for e in events if e.get("date") == today]
        if not today_events:
            return "Nenhum evento para hoje"
        return "Eventos de hoje:\n" + "\n".join(f"- {e['title']}" for e in today_events)
    except Exception as e:
        return f"Erro: {e}"


# ========================
# DEPLOY / BACKUP
# ========================

# ========================
# PROGRAMAÇÃO
# ========================

def generate_code(language: str, description: str) -> str:
    """Gera código na linguagem especificada baseado na descrição."""
    if not description:
        return "Informe a descrição do código a gerar."
    try:
        from core.minimax_client import get_client
        client = get_client()
        prompt = f"""Gere código em {language or 'Python'} para: {description}
Retorne apenas o código, sem explicações. Use markdown com ``` para destacar o código."""
        result = client._call_llm(prompt)
        return f"```\n{result}\n```" if result else "Não consegui gerar o código."
    except Exception as e:
        return f"Erro ao gerar código: {e}"


def fix_bugs(code: str, language: str = "") -> str:
    """Corrige bugs no código fornecido."""
    if not code:
        return "Informe o código com bugs."
    try:
        from core.minimax_client import get_client
        client = get_client()
        prompt = f"""Analise e corrija os bugs no seguinte código ({language or 'Python'}):
```{code}```
Retorne o código corrigido com uma breve explicação das correções."""
        result = client._call_llm(prompt)
        return f"Código corrigido:\n```\n{result}\n```" if result else "Não consegui corrigir o código."
    except Exception as e:
        return f"Erro ao corrigir bugs: {e}"


def refactor_code(code: str, language: str = "") -> str:
    """Refatora o código para melhor qualidade."""
    if not code:
        return "Informe o código a refatorar."
    try:
        from core.minimax_client import get_client
        client = get_client()
        prompt = f"""Refatore o seguinte código ({language or 'Python'}) para melhor legibilidade e performance:
```{code}```
Retorne o código refatorado com uma breve explicação."""
        result = client._call_llm(prompt)
        return f"Código refatorado:\n```\n{result}\n```" if result else "Não consegui refatorar o código."
    except Exception as e:
        return f"Erro ao refatorar código: {e}"


def generate_html(description: str) -> str:
    """Gera código HTML baseado na descrição."""
    if not description:
        return "Informe a descrição do HTML a gerar."
    try:
        from core.minimax_client import get_client
        client = get_client()
        prompt = f"""Gere código HTML completo e bem estruturado para: {description}
Retorne apenas o código HTML válido."""
        result = client._call_llm(prompt)
        return f"```html\n{result}\n```" if result else "Não consegui gerar o HTML."
    except Exception as e:
        return f"Erro ao gerar HTML: {e}"


def generate_css(description: str) -> str:
    """Gera código CSS baseado na descrição."""
    if not description:
        return "Informe a descrição do CSS a gerar."
    try:
        from core.minimax_client import get_client
        client = get_client()
        prompt = f"""Gere código CSS para: {description}
Retorne apenas o código CSS válido."""
        result = client._call_llm(prompt)
        return f"```css\n{result}\n```" if result else "Não consegui gerar o CSS."
    except Exception as e:
        return f"Erro ao gerar CSS: {e}"


def generate_api(framework: str, name: str) -> str:
    """Gera estrutura de API REST."""
    if not name:
        return "Informe o nome da API."
    framework = framework or "flask"
    try:
        from core.minimax_client import get_client
        client = get_client()
        prompt = f"""Gere a estrutura básica de uma API REST em {framework} chamada {name}.
Inclua: rotas principais, models básicos, configuração.
Retorne apenas o código."""
        result = client._call_llm(prompt)
        return f"```python\n{result}\n```" if result else "Não consegui gerar a API."
    except Exception as e:
        return f"Erro ao gerar API: {e}"


# ========================
# VS CODE
# ========================

def vscode_create_project(project_name: str, template: str = "") -> str:
    """Cria um novo projeto no VS Code."""
    if not project_name:
        return "Informe o nome do projeto."
    try:
        from config.settings import BASE_DIR
        project_path = BASE_DIR / project_name
        if project_path.exists():
            return f"Projeto já existe: {project_path}"
        project_path.mkdir(parents=True, exist_ok=True)
        if template:
            create_file(str(project_path / "README.md"), f"# {project_name}\n\nTemplate: {template}")
        subprocess.Popen(["/usr/bin/code", str(project_path)])
        return f"Projeto {project_name} criado e aberto no VS Code"
    except Exception as e:
        return f"Erro ao criar projeto: {e}"


def vscode_edit_file(file_path: str, content: str) -> str:
    """Edita um arquivo no VS Code."""
    if not file_path:
        return "Informe o caminho do arquivo."
    try:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        Path(file_path).write_text(content or "", encoding="utf-8")
        subprocess.Popen(["/usr/bin/code", file_path])
        return f"Arquivo {file_path} aberto no VS Code"
    except Exception as e:
        return f"Erro ao editar arquivo: {e}"


def vscode_install_extension(extension_id: str) -> str:
    """Instala uma extensão no VS Code."""
    if not extension_id:
        return "Informe o ID da extensão."
    try:
        result = subprocess.run(["code", "--install-extension", extension_id],
                             capture_output=True, text=True)
        if result.returncode == 0:
            return f"Extensão {extension_id} instalada com sucesso"
        return f"Erro ao instalar extensão: {result.stderr}"
    except Exception as e:
        return f"Erro ao instalar extensão: {e}"


def vscode_open(path: str) -> str:
    """Abre arquivo ou pasta no VS Code."""
    if not path:
        return "Informe o caminho."
    try:
        subprocess.Popen(["/usr/bin/code", path])
        return f"Aberto no VS Code: {path}"
    except Exception as e:
        return f"Erro ao abrir no VS Code: {e}"


# ========================
# NAVEGADOR
# ========================

def browser_automate(task: str) -> str:
    """Automatiza tarefas no navegador."""
    if not task:
        return "Informe a tarefa a automatizar."
    try:
        import pyautogui
        import webbrowser
        webbrowser.open("https://www.google.com")
        time.sleep(2)
        pyautogui.hotkey("ctrl", "l")
        pyautogui.write(task, interval=0.05)
        pyautogui.press("enter")
        return f"Automatizando tarefa: {task}"
    except Exception as e:
        return f"Erro ao automatizar: {e}"


def browser_fill_form(url: str, fields: str) -> str:
    """Preenche formulário web."""
    if not url:
        return "Informe a URL do formulário."
    try:
        import json
        fields_dict = json.loads(fields) if fields else {}
        webbrowser.open(url)
        time.sleep(3)
        for field_name, value in fields_dict.items():
            pyautogui.write(str(value), interval=0.05)
            pyautogui.press("tab")
        return f"Formulário preenchido com {len(fields_dict)} campos"
    except json.JSONDecodeError:
        return "Formato de campos inválido. Use JSON."
    except Exception as e:
        return f"Erro ao preencher formulário: {e}"


def browser_navigate(url: str) -> str:
    """Navega para URL no navegador."""
    if not url:
        return "Informe a URL."
    if not url.startswith("http"):
        url = "https://" + url
    try:
        webbrowser.open(url)
        return f"Navegando para: {url}"
    except Exception as e:
        return f"Erro ao navegar: {e}"


# ========================
# GITHUB AUTO
# ========================

def github_auto_commit() -> str:
    """Faz commit automático com mensagem gerada."""
    try:
        from config.settings import BASE_DIR
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=BASE_DIR)
        if not result.stdout.strip():
            return "Nada para commitar"
        subprocess.run(["git", "add", "."], cwd=BASE_DIR)
        result = subprocess.run(["git", "diff", "--staged"], capture_output=True, text=True, cwd=BASE_DIR)
        changes = result.stdout[:200] if result.stdout else "alterações"
        commit_msg = f"Update: {changes[:50]}..."
        result = subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, text=True, cwd=BASE_DIR)
        return f"Commit automático: {commit_msg}"
    except Exception as e:
        return f"Erro no commit: {e}"


def github_auto_push() -> str:
    """Faz push automático."""
    try:
        from config.settings import BASE_DIR
        result = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=BASE_DIR)
        if result.returncode == 0:
            return "Push automático realizado"
        return f"Erro no push: {result.stderr}"
    except Exception as e:
        return f"Erro ao fazer push: {e}"


def github_auto_pull() -> str:
    """Faz pull automático."""
    try:
        from config.settings import BASE_DIR
        result = subprocess.run(["git", "pull"], capture_output=True, text=True, cwd=BASE_DIR)
        if result.returncode == 0:
            return "Pull automático realizado"
        return f"Erro no pull: {result.stderr}"
    except Exception as e:
        return f"Erro ao fazer pull: {e}"


# ========================
# DEPLOY / BACKUP
# ========================

def deploy() -> str:
    """Executa deploy do projeto."""
    try:
        import subprocess
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        commit_msg = f"Deploy Jarvis - {timestamp}"

        # Verificar se é um repositório git
        result = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
 capture_output=True, text=True)
        if result.returncode != 0:
            return "Erro: Não é um repositório git"

        # git add .
        subprocess.run(["git", "add", "-A"], capture_output=True)

        # git status para ver o que mudou
        status = subprocess.run(["git", "status", "--porcelain"],
                               capture_output=True, text=True)

        if not status.stdout.strip():
            return "Nada para commitar - tudo já está atualizado"

        # git commit
        commit = subprocess.run(["git", "commit", "-m", commit_msg],
                               capture_output=True, text=True)

        if commit.returncode != 0:
            return f"Erro no commit: {commit.stderr}"

        # git push
        push = subprocess.run(["git", "push"],
 capture_output=True, text=True, timeout=30)

        if push.returncode == 0:
            return f"✅ Deploy realizado com sucesso!\n📝 Commit: {commit_msg}"
        else:
            return f"⚠️ Commit feito, mas push falhou: {push.stderr}"

    except subprocess.TimeoutExpired:
        return "⏰ Timeout no push - rede lenta ou offline"
    except Exception as e:
        return f"Erro no deploy: {e}"


def backup_dotfiles() -> str:
    try:
        home = Path.home()
        result = subprocess.run(["tar", "-czf", str(home / "dotfiles_backup.tar.gz"),
                               str(home / ".bashrc"), str(home / ".zshrc")],
                              capture_output=True, text=True)
        if result.returncode == 0:
            return f"Backup criado: {home}/dotfiles_backup.tar.gz"
        return f"Erro no backup: {result.stderr}"
    except Exception as e:
        return f"Erro ao fazer backup: {e}"


# ========================
# MACHINE LEARNING / STATS
# ========================

def show_stats() -> str:
    """Mostra estatísticas de uso do Jarvis."""
    try:
        from ml.usage_analytics import get_weekly_report
        return get_weekly_report()
    except ImportError:
        return "Módulo de analytics não disponível"
    except Exception as e:
        return f"Erro ao buscar estatísticas: {e}"


def show_ml_stats() -> str:
    """Mostra estatísticas do modelo de ML."""
    try:
        from ml.command_predictor import get_stats
        stats = get_stats()

        if stats["total_commands"] == 0:
            return "Sem dados suficientes para análise de ML. Continue usando o Jarvis!"

        lines = [
            "🧠 Estatísticas de Machine Learning",
            "=" * 35,
            f"Total de comandos: {stats['total_commands']}",
            f"Ações únicas: {stats['unique_actions']}",
            "",
            "📈 Top 5 ações:",
        ]

        for i, (action, count) in enumerate(stats["top_actions"], 1):
            lines.append(f"  {i}. {action}: {count}x")

        return "\n".join(lines)
    except ImportError:
        return "Módulo de ML não disponível"
    except Exception as e:
        return f"Erro ao buscar estatísticas de ML: {e}"


def train_ml() -> str:
    """Treina o modelo de ML com os dados coletados."""
    try:
        from ml.trainer import train_model
        result = train_model()

        if result["status"] == "insufficient_data":
            return f"📚 Dados insuficientes: {result['samples']}/5 necessários. Continue usando o Jarvis!"

        return (f"✅ Modelo treinado!\n"
                f"   Amostras: {result['samples']}\n"
                f"   Accuracy: {result['accuracy']:.1f}%\n"
                f"   Padrões aprendidos: {result['patterns_learned']}")
    except ImportError:
        return "Módulo de treinamento não disponível"
    except Exception as e:
        return f"Erro no treinamento: {e}"


def feedback(command: str, predicted: str, correct: str = None, rating: str = "0") -> str:
    """
    Registra feedback do usuário para melhorar o modelo.
    Uso: feedback "comando" "ação prevista" "ação correta" "rating"
    rating: -1 (errado), 0 (neutro), 1 (correto)
    """
    try:
        from ml.trainer import add_feedback

        rating_int = int(rating) if rating else 0

        if correct:
            add_feedback(command, predicted, correct, rating_int)
        else:
            add_feedback(command, predicted, None, rating_int)

        if correct and correct != predicted:
            return f"📝 Feedback registrado: '{command}' → {correct} (corrigido de {predicted})"
        elif rating_int == 1:
            return f"👍 Feedback positivo registrado para '{command}'"
        elif rating_int == -1:
            return f"👎 Feedback negativo registrado para '{command}' → {predicted}"
        else:
            return f"📝 Feedback registrado para '{command}'"
    except ImportError:
        return "Módulo de treinamento não disponível"
    except Exception as e:
        return f"Erro ao registrar feedback: {e}"


def training_status() -> str:
    """Mostra status atual do treinamento."""
    try:
        from ml.trainer import get_training_stats
        stats = get_training_stats()

        lines = [
            "📊 Status do Treinamento",
            "=" * 30,
            f"Total de feedback: {stats['total_feedback']}",
            f"Amostras de treino: {stats['training_samples']}",
            f"Correções: {stats['corrections']}",
            f"Confirmações: {stats['confirmations']}",
        ]

        if stats['last_update']:
            lines.append(f"Último comando: {stats['last_update'][:50]}...")

        if stats['training_samples'] < 5:
            lines.append("")
            lines.append("💡 Dica: Use 'feedback' para ensinar o Jarvis!")

        return "\n".join(lines)
    except ImportError:
        return "Módulo de treinamento não disponível"
    except Exception as e:
        return f"Erro ao buscar status: {e}"


# ========================
# REINFORCEMENT LEARNING
# ========================

def rl_reward(action: str, reward_type: str = "correct", context: str = "") -> str:
    """
    Registra recompensa para uma ação (Aprendizado por Reforço).
    reward_type: "correct" (+1.0), "incorrect" (-0.5), "neutral" (0.0)
    context: contexto opcional (ex: "browser", "system", "files")
    """
    try:
        from ml.reinforcement_learning import reward_action

        result = reward_action(action, reward_type, context)

        reward_symbol = "✅" if result["reward"] > 0 else "❌" if result["reward"] < 0 else "➖"

        return (f"{reward_symbol} Recompensa registrada!\n"
                f"   Ação: {result['action']}\n"
                f"   Pontos: {result['reward']:+.1f}\n"
                f"   Total: {result['total_score']:.1f} pts\n"
                f"   Usada: {result['times_used']}x")
    except ImportError:
        return "Módulo de RL não disponível"
    except Exception as e:
        return f"Erro ao registrar recompensa: {e}"


def rl_best_action(context: str = "") -> str:
    """Retorna a melhor ação baseada no histórico de RL."""
    try:
        from ml.reinforcement_learning import get_best_action

        result = get_best_action(context)

        if result["action"] is None:
            return "📚 Sem dados suficientes. Use 'rl_reward' para ensinar!"

        return (f"🎯 Melhor ação para '{context or 'geral'}':\n"
                f"   Ação: {result['action']}\n"
                f"   Score: {result['score']:.1f}\n"
                f"   Confiança: {result['confidence']:.0%}\n"
                f"   Fonte: {result['source']}")
    except ImportError:
        return "Módulo de RL não disponível"
    except Exception as e:
        return f"Erro ao buscar melhor ação: {e}"


def rl_report() -> str:
    """Mostra relatório completo do sistema de RL."""
    try:
        from ml.reinforcement_learning import get_learning_report
        return get_learning_report()
    except ImportError:
        return "Módulo de RL não disponível"
    except Exception as e:
        return f"Erro ao gerar relatório: {e}"


def rl_stats(action: str = "") -> str:
    """Mostra estatísticas detalhadas de uma ação no RL."""
    try:
        from ml.reinforcement_learning import get_action_stats

        if not action:
            return "Informe o nome da ação (ex: rl_stats open_app)"

        stats = get_action_stats(action)

        trend = "📈" if stats["trend"] == "up" else "📉"

        return (f"📊 Estatísticas de RL para '{action}':\n"
                f"   Score total: {stats['total_score']:.1f}\n"
                f"   Vezes usada: {stats['times_used']}\n"
                f"   Média por uso: {stats['avg_score']:.2f}\n"
                f"   Tendência: {trend}")
    except ImportError:
        return "Módulo de RL não disponível"
    except Exception as e:
        return f"Erro ao buscar estatísticas: {e}"


def rl_approve(action: str, context: str = "") -> str:
    """Aprova uma ação (recompensa positiva +1.0)."""
    return rl_reward(action, "correct", context)


def rl_reject(action: str, context: str = "") -> str:
    """Rejeita uma ação (recompensa negativa -0.5)."""
    return rl_reward(action, "incorrect", context)


# ========================
# PROJECT ANALYZER
# ========================

def analyze_project(path: str = "") -> str:
    """Analisa um projeto completo e gera relatório."""
    if not path:
        return "Informe o caminho do projeto a analisar."

    try:
        from analyzer import analyze_project, generate_analysis_report

        result = analyze_project(path)

        if result.score == 0 and not result.issues:
            return f"Projeto não encontrado: {path}"

        report = generate_analysis_report(result)

        # Registrar para ML
        try:
            from analyzer.analyzer_ml import record_analysis
            record_analysis(
                result.project_name,
                [i.to_dict() for i in result.issues],
                result.suggestions_accepted,
                result.suggestions_rejected
            )
        except:
            pass

        return report

    except ImportError:
        return "Módulo de análise não disponível. Instale as dependências."
    except Exception as e:
        return f"Erro ao analisar projeto: {e}"


def analyzer_report() -> str:
    """Mostra relatório do sistema de análise de projetos."""
    try:
        from analyzer.analyzer_ml import get_learning_report
        return get_learning_report()
    except ImportError:
        return "Módulo de análise não disponível"
    except Exception as e:
        return f"Erro ao gerar relatório: {e}"


def analyzer_ml_status() -> str:
    """Mostra status do sistema de ML do analyzer."""
    try:
        from analyzer.analyzer_ml import get_analyzer_ml

        ml = get_analyzer_ml()
        strategies = ml.get_strategy_ranking()

        lines = [
            "🧠 Analyzer ML - Status do Sistema",
            "=" * 45,
            f"Taxa de exploração: {ml.exploration_rate:.0%}",
            "",
            "🏆 Top 5 Estratégias:",
        ]

        if not strategies:
            lines.append("  Nenhuma estratégia aprendida ainda.")
        else:
            for i, s in enumerate(strategies[:5], 1):
                lines.append(
                    f"  {i}. {s['type']}: "
                    f"aceite={s['acceptance_rate']:.0%} "
                    f"precisão={s['accuracy']:.0%}"
                )

        lines.append("")
        lines.append("💡 Use 'analyzer_feedback' para ensinar o sistema!")

        return "\n".join(lines)
    except ImportError:
        return "Módulo de análise não disponível"
    except Exception as e:
        return f"Erro ao buscar status: {e}"


def analyzer_feedback(issue_type: str, rule_id: str = "", accepted: str = "true",
                    fixed: str = "false") -> str:
    """
    Registra feedback do usuário sobre uma análise.
    Uso: analyzer_feedback "security" "hardcoded_secret" "true" "true"
    """
    try:
        from analyzer.analyzer_ml import record_feedback

        # Handle both string and bool inputs
        if isinstance(accepted, bool):
            accepted_bool = accepted
        else:
            accepted_bool = accepted.lower() in ["true", "sim", "1", "yes"]

        if isinstance(fixed, bool):
            fixed_bool = fixed
        else:
            fixed_bool = fixed.lower() in ["true", "sim", "1", "yes"]

        reward = record_feedback(issue_type, rule_id, accepted_bool, fixed_bool if accepted_bool else None)

        if reward > 1.5:
            return f"✅ Excelente! Análise correta + problema realmente resolvido! (+{reward:.1f})"
        elif reward > 0:
            return f"👍 Feedback positivo registrado (+{reward:.1f})"
        elif reward < 0:
            return f"👎 Feedback negativo registrado ({reward:.1f})"
        else:
            return f"➖ Feedback registrado (neutro)"

    except ImportError:
        return "Módulo de análise não disponível"
    except Exception as e:
        return f"Erro ao registrar feedback: {e}"


# ========================
# RUN COMMAND
# ========================

def run_command(command: str) -> str:
    if not command:
        return "Informe o comando a executar."
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout.strip() or result.stderr.strip() or "Comando executado (sem output)"
        return f"Output:\n{output}"
    except Exception as e:
        return f"Erro ao executar comando: {e}"


# ========================
# Dicionário de funções
# ========================

FUNCTIONS = {
    # Sistema
    "search_web": search_web,
    "open_app": open_app,
    "open_site": open_site,
    "close_app": close_app,
    "shutdown_pc": shutdown_pc,
    "schedule_shutdown": schedule_shutdown,
    "cancel_shutdown": cancel_shutdown,
    "restart_pc": restart_pc,
    "hibernate_pc": hibernate_pc,
    "sleep_mode": sleep_mode,
    "wifi_on": wifi_on,
    "wifi_off": wifi_off,
    "set_brightness": set_brightness,

    # Volume/Mídia
    "volume_up": volume_up,
    "volume_down": volume_down,
    "mute": mute,
    "spotify_play": spotify_play,
    "spotify_pause": spotify_pause,
    "spotify_next": spotify_next,
    "spotify_previous": spotify_previous,

    # Arquivos
    "open_folder": open_folder,
    "create_file": create_file,
    "read_file": read_file,
    "delete_file": delete_file,
    "rename_file": rename_file,
    "move_file": move_file,
    "copy_file": copy_file,
    "organize_folder": organize_folder,
    "find_file": find_file,

    # Git
    "git_status": git_status,
    "git_log": git_log,
    "git_pull": git_pull,
    "git_push": git_push,
    "git_commit": git_commit,

    # Monitoramento
    "hardware_status": hardware_status,
    "disk_health": disk_health,
    "internet_speed": internet_speed,

    # Automação
    "type_text": type_text,
    "press_key": press_key,
    "click_mouse": click_mouse,
    "move_mouse": move_mouse,
    "hotkey": hotkey,
    "screenshot": screenshot,

    # Lembretes/Tarefas
    "add_reminder": add_reminder,
    "list_reminders": list_reminders,
    "add_task": add_task,
    "list_tasks": list_tasks,

    # Despertador
    "set_alarm": set_alarm,
    "cancel_alarm": cancel_alarm,
    "list_alarms": list_alarms,
    "play_alarm_sound": play_alarm_sound,

    # Agenda
    "add_event": add_event,
    "calendar_today": calendar_today,

    # Despesas
    "add_expense": add_expense,
    "expense_summary": expense_summary,

    # Deploy
    "deploy": deploy,
    "backup_dotfiles": backup_dotfiles,
    "schedule_deploy": schedule_deploy,
    "cancel_deploy_schedule": cancel_deploy_schedule,
    "list_deploy_schedules": list_deploy_schedules,

    # ML/Stats
    "show_stats": show_stats,
    "show_ml_stats": show_ml_stats,
    "train_ml": train_ml,
    "feedback": feedback,
    "training_status": training_status,

    # RL (Aprendizado por Reforço)
    "rl_reward": rl_reward,
    "rl_best_action": rl_best_action,
    "rl_report": rl_report,
    "rl_stats": rl_stats,
    "rl_approve": rl_approve,
    "rl_reject": rl_reject,

    # Analyzer (Análise de Projetos)
    "analyze_project": analyze_project,
    "analyzer_report": analyzer_report,
    "analyzer_ml_status": analyzer_ml_status,
    "analyzer_feedback": analyzer_feedback,

    # Comandos
    "run_command": run_command,

    # Programação
    "generate_code": generate_code,
    "fix_bugs": fix_bugs,
    "refactor_code": refactor_code,
    "generate_html": generate_html,
    "generate_css": generate_css,
    "generate_api": generate_api,

    # VS Code
    "vscode_create_project": vscode_create_project,
    "vscode_edit_file": vscode_edit_file,
    "vscode_install_extension": vscode_install_extension,
    "vscode_open": vscode_open,

    # Navegador
    "browser_automate": browser_automate,
    "browser_fill_form": browser_fill_form,
    "browser_navigate": browser_navigate,

    # GitHub Auto
    "github_auto_commit": github_auto_commit,
    "github_auto_push": github_auto_push,
    "github_auto_pull": github_auto_pull,
}


def execute_action(action: str, target: str = "", parameters: dict = None) -> str:
    if action == "chat" or action == "error":
        return target

    func = FUNCTIONS.get(action)
    if func is None:
        return f"Ação desconhecida: {action}"

    params = parameters or {}

    try:
        # Funções com parâmetro único (target)
        single_param_actions = ["search_web", "open_app", "open_site", "close_app", "open_folder",
                                "create_file", "read_file", "delete_file", "organize_folder",
                                "find_file", "git_status", "git_log", "git_pull", "git_push",
                                "disk_health", "internet_speed",
                                "list_reminders", "list_tasks", "calendar_today", "expense_summary",
                                "run_command", "schedule_shutdown", "list_alarms", "play_alarm_sound"]

        if action in single_param_actions:
            first_param = params.get("query") or params.get("app_name") or params.get("url") or \
                          params.get("path") or params.get("filename") or params.get("command") or \
                          params.get("target") or target
            return func(first_param)

        # Funções com dois parâmetros
        two_param_actions = ["rename_file", "move_file", "copy_file", "add_expense"]
        if action in two_param_actions:
            if action == "rename_file":
                return func(old_path=params.get("old_path", target), new_name=params.get("new_name", ""))
            elif action == "move_file":
                return func(source=params.get("source", target), destination=params.get("destination", ""))
            elif action == "copy_file":
                return func(source=params.get("source", target), destination=params.get("destination", ""))
            elif action == "add_expense":
                return func(amount=params.get("amount", target), description=params.get("description", ""))

        # Funções sem parâmetros
        no_param_actions = ["volume_up", "volume_down", "mute", "shutdown_pc", "restart_pc",
                           "hibernate_pc", "sleep_mode", "wifi_on", "wifi_off",
                           "spotify_play", "spotify_pause", "spotify_next", "spotify_previous",
                           "click_mouse", "screenshot", "deploy", "backup_dotfiles", "cancel_shutdown",
                           "hardware_status", "show_stats", "show_ml_stats", "list_deploy_schedules"]
        if action in no_param_actions:
            return func()

        # Funções que usam o target como parâmetro
        if action in ["type_text", "press_key"]:
            return func(params.get("text") or params.get("keys") or target)

        if action in ["add_reminder", "add_task", "add_event"]:
            return func(params.get("text") or target)

        if action == "set_brightness":
            return func(params.get("level") or params.get("brightness") or target)

        if action == "move_mouse":
            return func(params.get("x") or target, params.get("y") or params.get("y_coord", "0"))

        # Funções com hotkey
        if action == "hotkey":
            keys = params.get("keys") or target
            if isinstance(keys, str):
                keys = keys.split("+")
            return func(*keys)

        # Funções com git_commit
        if action == "git_commit":
            return func(params.get("message") or target)

        # Programação
        if action == "generate_code":
            return func(params.get("language") or "", params.get("description") or target)
        if action == "fix_bugs":
            return func(params.get("code") or target, params.get("language") or "")
        if action == "refactor_code":
            return func(params.get("code") or target, params.get("language") or "")
        if action == "generate_html":
            return func(params.get("description") or target)
        if action == "generate_css":
            return func(params.get("description") or target)
        if action == "generate_api":
            return func(params.get("framework") or "flask", params.get("name") or target)

        # VS Code
        if action == "vscode_create_project":
            return func(params.get("project_name") or target, params.get("template") or "")
        if action == "vscode_edit_file":
            return func(params.get("file_path") or target, params.get("content") or "")
        if action == "vscode_install_extension":
            return func(params.get("extension_id") or target)
        if action == "vscode_open":
            return func(params.get("path") or target)

        # Navegador
        if action == "browser_automate":
            return func(params.get("task") or target)
        if action == "browser_fill_form":
            return func(params.get("url") or target, params.get("fields") or "{}")
        if action == "browser_navigate":
            return func(params.get("url") or target)

        # Despertador
        if action == "set_alarm":
            return func(params.get("time") or target, params.get("recurring") or "")
        if action == "cancel_alarm":
            return func(params.get("time") or target)

        # Deploy agendado
        if action == "schedule_deploy":
            return func(params.get("time") or target, params.get("recurring") or "")
        if action == "cancel_deploy_schedule":
            return func(params.get("time") or target)

        # GitHub Auto
        if action in ["github_auto_commit", "github_auto_push", "github_auto_pull"]:
            return func()

        # Deploy sem argumentos
        if action in ["deploy", "backup_dotfiles"]:
            return func()

        return func(target)

    except Exception as e:
        return f"Erro ao executar {action}: {e}"