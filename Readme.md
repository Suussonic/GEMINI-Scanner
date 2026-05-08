# 🔎 GEMINI Scanner 

Répertoire permettant de scanner l'écran et l'envoi à gemini.

## 📜 Sommaire
- [Dépendances](#🐍dépendances)
- [API](#🔑api)
- [Fichier ENV](#⚙️fichier-env)

# 🐍 Dépendances

Ce script réaliser en python utiliser des bibliothéques et il important de les installer pour eviter tous problémes :

    pip install python-dotenv pyperclip keyboard Pillow winotify google-generativeai


# 🔑 API

Ce script utilise la technologie gemini pour pouvoir fonctionner correctement, il est donc important de recupérer une clé, pour ce faire rendez-vous sur ce site :

https://aistudio.google.com/apikey

Vous pourrais créer des clés, à noter que pour acceder a la plateforme il faut une addresse mail dont l'âge est verifier.

# ⚙️ Fichier ENV

Pour fonctionner correctement, il vous faudra créer un fichier .env dans le même dossier que votre script python et il y faudra y inscrire les informations suivantes :


    # Clé API Google Gemini
    GEMINI_API_KEY=Votre_clé_api_gemini

    # Taille de la capture d'écran
    CAPTURE_BBOX=0,0,1920,1080

    # Model utilisé
    GEMINI_MODEL=gemini-2.5-pro 

    #Afficher les Popup
    SHOW_POPUP=FALSE

    # Affichage de la popup (nouvelle variable principale)
    SHOWWINDOWSPOPUP=true

    # Écriture automatique dans la fenêtre active
    AUTOWRITER=true
    
    # Mode de timing réel (delais humains). Mettre false pour écriture rapide.
    REALTIMING=true

    # Message / prompt envoyé à Gemini
    MESSAGE=Analyse cette image et donne une réponse concise à la question qu'elle contient, sans détail :

    # Mettre HUMANSPEED=true pour activer, false pour garder le comportement interne
    HUMANSPEED=true

    # Définissez ici la combinaison clavier qui déclenche la capture/analyse.
    INPUT=ctrl+alt+g

    INPUT=ctrl+alt+g

    # Raccourci pour arrêter la frappe en cours (stopinput)
    STOPINPUT=ctrl+alt+s

    # Raccourci pour mettre en pause / reprendre la frappe
    PAUSEINPUT=ctrl+alt+p

    # Raccourci pour terminer complètement le programme (endinput)
    ENDINPUT=F10