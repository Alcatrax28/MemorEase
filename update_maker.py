import os
import requests  # pyright: ignore[reportMissingModuleSource]
import tempfile
import subprocess
import json
from utils import resource_path, VERSION_FILE  # pyright: ignore[reportMissingImports]

# Chemin vers version.txt (même logique que dans main.py)
VERSION_FILE = resource_path(os.path.join("assets", "version.txt"))

TEST_LOCAL = False
LATEST_JSON_URL = "https://raw.githubusercontent.com/Alcatrax28/MemorEase/main/latest.json"
TEMP_EXE_NAME = "MemorEase_Update.exe"

# --- Lecture de la version locale ---
def get_local_version():
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip().lstrip("v")
    except FileNotFoundError:
        return "0.0.0"

# --- Lecture des infos distantes ---
def get_remote_info():
    try:
        if TEST_LOCAL:
            with open("latest.json", "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            r = requests.get(LATEST_JSON_URL, timeout=5)
            if r.status_code == 200:
                return r.json()
    except Exception:
        return None

# --- Comparaison des versions ---
def normalize_version(v):
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except ValueError:
        return (0, 0, 0)

def is_update_available(local_version, remote_version):
    return normalize_version(remote_version) > normalize_version(local_version)

# --- Vérification de mise à jour ---
def check_for_update():
    local = get_local_version()
    remote_data = get_remote_info()
    if not remote_data:
        return None, local, None

    remote_version = remote_data.get("version", "0.0.0")
    if is_update_available(local, remote_version):
        return {
            "new_version": remote_version,
            "url": remote_data.get("url"),
            "changelog": remote_data.get("changelog", []),
            "mandatory": remote_data.get("mandatory", False)
        }, local, remote_version

    return None, local, remote_version

# --- Téléchargement du fichier de mise à jour ---
def download_update(url, log_callback=None, progress_callback=None, cancel_flag=None):
    try:
        r = requests.get(url, stream=True, timeout=10)

        # Vérifie que le lien pointe bien vers un fichier binaire
        content_type = r.headers.get("Content-Type", "")
        if "text/html" in content_type:
            if log_callback: log_callback("Le lien ne pointe pas vers un fichier exécutable.")
            return None

        total_size = int(r.headers.get('content-length', 0))
        temp_path = os.path.join(tempfile.gettempdir(), TEMP_EXE_NAME)

        with open(temp_path, "wb") as f:
            downloaded = 0
            for chunk in r.iter_content(chunk_size=8192):
                if cancel_flag and cancel_flag.cancelled:
                    if log_callback: log_callback("Téléchargement annulé.")
                    return None
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total_size)

        # Vérifie que le fichier est suffisamment grand pour être valide
        if os.path.getsize(temp_path) < 1024:
            if log_callback: log_callback("Fichier téléchargé trop petit ou invalide.")
            return None

        if log_callback: log_callback(f"Téléchargement terminé : {temp_path}")
        return temp_path

    except Exception as e:
        if log_callback: log_callback(f"Erreur : {e}")
        return None

# --- Lancement de la nouvelle version ---
def launch_new_version(new_exe_path, log_callback=None):
    if not os.path.exists(new_exe_path):
        if log_callback: log_callback("Fichier de mise à jour introuvable.")
        return False

    if os.path.getsize(new_exe_path) < 1024:
        if log_callback: log_callback("Fichier de mise à jour invalide ou corrompu. Abandon du lancement.")
        return False

    if log_callback: log_callback("Lancement de la nouvelle version...")
    subprocess.Popen([new_exe_path], shell=True)
    os._exit(0)  # Fermeture immédiate pour éviter le code 5 d'Inno Setup