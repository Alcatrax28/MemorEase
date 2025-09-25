import os
import sys
import json
import getpass
import string
import hashlib
import imagehash        # pyright: ignore[reportMissingImports]
from PIL import Image   # pyright: ignore[reportMissingImports]

# Intégration MEIPASS pour .exe, en cas d'erreur, chemin classique
def resource_path(relative_path: str) -> str:
    try:
        base_path = sys.MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Retourne les fichiers externes non intégrés au .exe (ex : config.json)
def external_path(relative_path: str) -> str:
    if getattr(sys, 'frozen', False):
        # Si .exe -> dossier du .exe
        base_path = os.path.dirname(sys.executable)
    else:
        # Si .py -> dossier du script exécuté (main.py)
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# Détecter le dossier Onedrive sur la machine
def find_onedrive():
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

# Retourner les chemins par défaut : Onedrive si trouvé, sinon les dossiers locaux usuels Windows
def get_default_paths():
    od = find_onedrive()
    user = getpass.getuser()
    if od:
        save    = os.path.join(od, "Memorease", "Download")
        photos  = os.path.join(od, "Memorease", "Images", "Photos")
        videos  = os.path.join(od, "Memorease", "Videos", "Mes videos")
    else:
        root_drive  = os.getcwd().split(os.sep)[0] + "\\"
        base        = os.path.join(root_drive, "Users", user)
        save        = os.path.join(base, "Pictures", "Memorease_Downloads")
        photos      = os.path.join(base, "Pictures", "Photos")
        videos      = os.path.join(base, "Videos", "Mes videos")
    return save, photos, videos

# Lien vers le fichier de configuration et de version
# Configuration (pour les emplacements de sauvegarde) -> NON embarqué et modifiable
CONFIG_FILE = external_path(os.path.join("assets", "config.json"))
# Version (embarqué)
VERSION_FILE = resource_path(os.path.join("assets", "version.txt"))

# Lecture du n° de version "version.txt" (embarqué dans le .exe)
def read_version() -> str:
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    # Si le fichier n'est pas trouvé, on retourne une valeur vide
    except FileNotFoundError:
        return ""
    
# Créer config.json avec les valeurs par défaut si le fichier est absent
if not os.path.isfile(CONFIG_FILE):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    save, photos, videos = get_default_paths()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "save": save,
            "photos": photos,
            "videos": videos
        }, f, indent=4, ensure_ascii=False)

# Charger les chemins depuis config.json (externe). Si le fichier rencontre une erreur, on retourne les valeurs par défaut
def load_paths():
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
        pass
    return get_default_paths

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