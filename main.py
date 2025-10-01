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

# Chargement des variables d'environnement (chemin absolu)
from dotenv import load_dotenv
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# ==== Nouvelles variables de configuration (popup supprimée) ====
# SHOWWINDOWSPOPUP retiré : l'application n'affiche plus de popup Tkinter
# Message envoyé à Gemini (prompt)
MESSAGE = os.getenv(
    "MESSAGE",
    "Analyse cette image et donne une réponse concise à la question qu'elle contient, sans détail :"
).strip()
# Ecriture automatique de la réponse dans la fenêtre active
AUTOWRITER = os.getenv("AUTOWRITER", "true").strip().lower() in ("1", "true", "yes", "on")

# ==== Configuration depuis .env (existante) ====
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "")
# CAPTURE_BBOX : validation + défaut
CAPTURE_BBOX_RAW = os.getenv("CAPTURE_BBOX", "0,0,800,600").strip()
try:
    CAPTURE_BBOX = tuple(map(int, CAPTURE_BBOX_RAW.split(',')))
    if len(CAPTURE_BBOX) != 4:
        raise ValueError
except Exception:
    print("Erreur: CAPTURE_BBOX doit être 4 entiers séparés par des virgules. Utilisation défaut 0,0,800,600")
    CAPTURE_BBOX = (0, 0, 800, 600)

LOG_FILE = os.getenv("LOG_FILE", "gemini_scanner.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# ==== Logger ====
logger = logging.getLogger("GeminiScanner")
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding='utf-8')
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)
else:
    # Evite doublons si rechargé
    already = any(isinstance(h, RotatingFileHandler) and getattr(h, 'baseFilename', '') == handler.baseFilename for h in logger.handlers)
    if not already:
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
        time.sleep(0.25)

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

# ---- Fonction pour écrire automatiquement la réponse ----

def type_answer(text: str):
    """Tape la réponse dans la fenêtre active, respecte \n."""
    if not text:
        return
    try:
        time.sleep(0.4)  # laisse le temps de se placer
        for ch in text:
            if ch == '\n':
                keyboard.send('enter')
            else:
                keyboard.write(ch)
            time.sleep(0.004)
        logger.info("Réponse écrite automatiquement (AUTOWRITER activé).")
    except Exception as e:
        logger.error(f"Erreur AUTOWRITER: {e}")


# ==== Capture écran et envoi à Gemini ====

def capture_et_analyse():
    logger.info("Début capture_et_analyse")
    # Toast unique après capture pour éviter clignotement
    try:
        screenshot = ImageGrab.grab(bbox=CAPTURE_BBOX)
        logger.info("Capture écran réussie")
        notify_toast("Gemini Scanner", "Image capturée, analyse en cours...")
    except Exception as e:
        logger.error(f"Erreur capture écran: {e}")
        notify_toast("Erreur capture", str(e))
        return

    buffer = BytesIO()
    screenshot.save(buffer, format="PNG")
    buffer.seek(0)
    image_part = Image.open(buffer)

    max_retries = 3
    delay = 2
    answer = None

    for attempt in range(1, max_retries + 1):
        try:
            response = gemini_model.generate_content([
                MESSAGE,
                image_part
            ])
            answer = (response.text or "").strip()
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
        notify_toast("Gemini Scanner", "Aucune réponse obtenue.")
        logger.error("Aucune réponse Gemini après plusieurs tentatives.")
        return

    notify_toast("Réponse Gemini", answer)

    # 1) Écriture automatique d'abord (sinon la popup prend le focus et la frappe s'arrête)
    if AUTOWRITER:
        type_answer(answer)

    # (Popup supprimée, plus d'affichage Tkinter)

    pyperclip.copy(answer)
    notify_toast("Gemini Scanner", "Réponse copiée (presse-papiers)")
    logger.info("Réponse copiée dans le presse-papiers")

# ==== Raccourcis clavier ==== 

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
