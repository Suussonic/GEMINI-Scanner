import os
import sys
import threading
import time
import pyperclip
import logging
from logging.handlers import RotatingFileHandler
import keyboard
from PIL import ImageGrab, Image
from io import BytesIO
import tkinter as tk
from tkinter import messagebox

# Chargement des variables d'environnement
from dotenv import load_dotenv
load_dotenv()

# ==== Configuration depuis .env ====
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "")
CAPTURE_BBOX = tuple(map(int, os.getenv("CAPTURE_BBOX", "").split(",")))
LOG_FILE = os.getenv("LOG_FILE", "gemini_scanner.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
SHOW_POPUP = os.getenv("SHOW_POPUP", "").strip()

# ==== Logger ====
logger = logging.getLogger("GeminiScanner")
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding='utf-8')
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.info("=== Démarrage du script Gemini Scanner (multimodal) ===")

# ==== Notifications via winotify ====
try:
    from winotify import Notification, audio
    USE_WINOTIFY = True
    logger.info("winotify disponible pour notifications")
except ImportError:
    USE_WINOTIFY = False
    logger.warning("winotify non disponible")

def notify_toast(title: str, message: str, duration: int = 5):
    if not USE_WINOTIFY:
        logger.info(f"[Notification] {title}: {message[:256]}")
        return
    text = message.strip()
    max_len = 300
    parts = []
    while text:
        parts.append(text[:max_len])
        text = text[max_len:]
    for idx, part in enumerate(parts):
        try:
            toast = Notification(
                app_id="GeminiScanner",
                title=(f"{title}" + (f" ({idx+1}/{len(parts)})" if len(parts) > 1 else "")),
                msg=part
            )
            toast.set_audio(audio.Default, loop=False)
            toast.show()
            logger.info(f"Notification affichée: {title} (part {idx+1})")
        except Exception as e:
            logger.error(f"Erreur notification: {e}")
        time.sleep(0.3)

# ==== Initialisation client Gemini multimodal ====
try:
    from google import generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(model_name=GEMINI_MODEL)
    logger.info("Client Gemini multimodal initialisé.")
except Exception as e:
    logger.error(f"Erreur initialisation Gemini: {e}")
    notify_toast("Erreur Gemini Init", str(e))
    sys.exit(1)

def get_clipboard_image():
    try:
        img = ImageGrab.grabclipboard()
        if isinstance(img, Image.Image):
            return img
        else:
            logger.warning("Aucune image dans le presse-papiers.")
            return None
    except Exception as e:
        logger.error(f"Erreur clipboard: {e}")
        return None

# ==== Overlay: Capture écran et envoi à Gemini ====
def capture_et_analyse():
    logger.info("Début capture_et_analyse")
    notify_toast("Gemini Scanner", "Analyse en cours (capture auto)...")

    try:
        screenshot = ImageGrab.grab(bbox=CAPTURE_BBOX)
        logger.info("Capture écran réussie")
    except Exception as e:
        logger.error(f"Erreur capture écran: {e}")
        notify_toast("Erreur capture", str(e))
        return

    buffer = BytesIO()
    screenshot.save(buffer, format="PNG")
    buffer.seek(0)
    image_part = Image.open(buffer)
    logger.info("Image convertie en mémoire")

    max_retries = 3
    delay = 2
    answer = None

    for attempt in range(1, max_retries + 1):
        try:
            response = gemini_model.generate_content([
                "Analyse cette image et donne une réponse concise à la question qu'elle contient, sans détail :",
                image_part
            ])
            answer = response.text.strip()
            pyperclip.copy(answer)
            logger.info(f"Réponse Gemini reçue ({len(answer)} caractères)")
            break
        except Exception as e:
            err_msg = str(e)
            logger.warning(f"Erreur Gemini (tentative {attempt}): {err_msg}")
            if '503' in err_msg or 'UNAVAILABLE' in err_msg:
                notify_toast("Gemini Scanner", f"Serveur occupé, retry {attempt}/{max_retries}...")
                time.sleep(delay)
                delay *= 2
            else:
                notify_toast("Erreur Gemini", err_msg)
                return

    if not answer:
        notify_toast("Erreur", "Aucune réponse obtenue de Gemini.")
        logger.error("Aucune réponse Gemini après plusieurs tentatives.")
        return

    pyperclip.copy(answer)  # Copie la réponse dans le presse-papiers
    notify_toast("Gemini Scanner", answer)
    time.sleep(2)
    notify_toast("Gemini Scanner", "Réponse copiée dans le presse-papiers.")

def show_popup(response):
    def popup():
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Réponse Gemini", response)
        root.destroy()
    threading.Thread(target=popup).start()

def log_gemini_response(response):
    try:
        with open("gemini_responses.log", "a", encoding="utf-8") as f:
            f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {response}\n")
        logger.info("Réponse enregistrée dans gemini_responses.log")
    except Exception as e:
        logger.error(f"Erreur log réponse: {e}")

# ==== Clavier : Ctrl+Alt+G = capture, F10 = arrêt ====
def ecoute_clavier():
    logger.info("Initialisation des raccourcis clavier")
    keyboard.add_hotkey('ctrl+alt+g', lambda: threading.Thread(target=capture_et_analyse, daemon=True).start())
    keyboard.add_hotkey('F10', lambda: (
        logger.info("Touche panic F10 pressée, arrêt du script."),
        os._exit(0)
    ))
    logger.info("En attente de Ctrl+Alt+G (capture) ou F10 (arrêt)")
    keyboard.wait()

if __name__ == "__main__":
    try:
        ecoute_clavier()
    except Exception as e:
        logger.error(f"Erreur principale: {e}")
    finally:
        logger.info("=== Fin du script Gemini Scanner ===")
