import os
import sys
import json
import getpass
import string
import hashlib
import imagehash        # pyright: ignore[reportMissingImports]
from PIL import Image   # pyright: ignore[reportMissingImports]

def resource_path(relative_path: str) -> str:
    """
    Retourne le chemin vers un fichier embarqué dans le bundle PyInstaller.
    Utilisé pour les ressources figées (icônes, changelog, etc.).
    """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def external_path(relative_path: str) -> str:
    """
    Retourne le chemin vers un fichier externe (non embarqué) à côté du .exe ou du script.
    Utilisé pour les fichiers modifiables comme config.json.
    """
    if getattr(sys, 'frozen', False):
        # En .exe → dossier de l'exécutable
        base_path = os.path.dirname(sys.executable)
    else:
        # En .py → dossier du script
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# Fichiers de configuration et version
CONFIG_FILE = external_path(os.path.join("assets", "config.json"))  # externe et modifiable
VERSION_FILE = resource_path(os.path.join("assets", "version.txt"))  # embarqué

def read_version() -> str:
    """Lit la version depuis version.txt (embarqué)."""
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""

def find_onedrive():
    """Détecte le dossier OneDrive sur la machine."""
    for drive in (f"{d}:\\" for d in string.ascii_uppercase):
        users_dir = os.path.join(drive, "Users")
        if not os.path.isdir(users_dir):
            continue
        for user_folder in os.listdir(users_dir):
            base = os.path.join(users_dir, user_folder)
            if not os.path.isdir(base):
                continue
            for name in ("OneDrive", "Onedrive", "onedrive"):
                path = os.path.join(base, name)
                if os.path.isdir(path):
                    return path
    return None

def file_md5(path, block_size=65536):
    md5 = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(block_size), b""):
            md5.update(chunk)
    return md5.hexdigest()

def image_hash(path):
    try:
        img = Image.open(path).convert("RGB")
        return imagehash.phash(img)
    except Exception:
        return None

def get_default_paths():
    """
    Retourne les chemins par défaut pour save, photos et vidéos.
    Utilise OneDrive si disponible, sinon les dossiers locaux.
    """
    od = find_onedrive()
    user = getpass.getuser()
    if od:
        save   = os.path.join(od, "Memorease", "Downloads")
        photos = os.path.join(od, "Memorease", "Photos")
        videos = os.path.join(od, "Memorease", "Mes videos")
    else:
        root_drive = os.getcwd().split(os.sep)[0] + "\\"
        base       = os.path.join(root_drive, "Users", user)
        save   = os.path.join(base, "Pictures", "Memorease_Downloads")
        photos = os.path.join(base, "Pictures", "Memorease_Photos")
        videos = os.path.join(base, "Videos", "Memorease_videos")
    return save, photos, videos

def ensure_config_exists():
    """
    Crée config.json avec les valeurs par défaut si le fichier est absent.
    """
    if not os.path.isfile(CONFIG_FILE):
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        save, photos, videos = get_default_paths()
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "save": save,
                "photos": photos,
                "videos": videos
            }, f, indent=4, ensure_ascii=False)

def load_paths():
    """
    Tente de charger les chemins depuis config.json (externe).
    Si le fichier est manquant, mal formé ou incomplet, retourne les valeurs par défaut.
    """
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            save, photos, videos = (
                data.get("save"),
                data.get("photos"),
                data.get("videos"),
            )
            if all(isinstance(p, str) and p for p in (save, photos, videos)):
                return save, photos, videos
    except Exception:
        pass  # Silencieux, fallback automatique

    return get_default_paths()