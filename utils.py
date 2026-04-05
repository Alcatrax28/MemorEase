import os
import sys
import json
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
    """
    home   = os.path.expanduser("~")
    base   = os.path.join(home, "OneDrive", "Images", "Memorease")
    save   = os.path.join(base, "tmp")
    photos = os.path.join(base, "Photos")
    videos = os.path.join(base, "Videos")
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
    Si le fichier est manquant, mal formé, incomplet ou contient des chemins
    Windows (ex: C:\\), retourne les valeurs par défaut Linux.
    """
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            save, photos, videos = (
                data.get("save"),
                data.get("photos"),
                data.get("videos"),
            )
            if all(isinstance(p, str) and p and p.startswith("/")
                   for p in (save, photos, videos)):
                return save, photos, videos
    except Exception:
        pass  # Silencieux, fallback automatique

    return get_default_paths()

def save_paths(save, photos, videos):
    """
    Sauvegarde les chemins dans config.json (externe), en préservant les autres clés (ex: backup).
    """
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    data.update({"save": save, "photos": photos, "videos": videos})
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_backup_path() -> str:
    """Lit le chemin de backup depuis config.json (externe)."""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            path = data.get("backup", "")
            if isinstance(path, str) and path.startswith("/"):
                return path
    except Exception:
        pass
    return ""

def save_backup_path(backup: str):
    """Sauvegarde uniquement le chemin de backup dans config.json, en préservant les autres clés."""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    data["backup"] = backup
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)