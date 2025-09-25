import subprocess
import os
import time
import sys
from utils import resource_path

def get_adb_path():
    adb_embedded = resource_path(os.path.join("assets", "adb", "adb.exe"))
    if os.path.isfile(adb_embedded):
        return adb_embedded
    return "adb"  # fallback système

ADB_PATH = get_adb_path()

startupinfo = None
if sys.platform == "win32":
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

def _list_all_files(root_dir):
    all_files = set()
    if os.path.isdir(root_dir):
        for dirpath, _, filenames in os.walk(root_dir):
            for f in filenames:
                all_files.add(f)
    return all_files

def run_adb_download(save_path, photos_path, videos_path,
                     log_callback, progress_callback, cancel_flag,
                     download_photos=True, download_videos=True):

    # --- Connexion ADB ---
    try:
        subprocess.run([ADB_PATH, "start-server"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       startupinfo=startupinfo)
        output = subprocess.check_output([ADB_PATH, "devices"],
                                         startupinfo=startupinfo).decode("utf-8", errors="ignore")
        output_lines = output.strip().splitlines()
    except Exception as e:
        log_callback(f"[ERREUR] Impossible d'exécuter adb : {repr(e)}")
        return

    if not output_lines or len(output_lines) < 2:
        log_callback("[ERREUR] Aucun appareil détecté (liste vide).")
        return

    device_lines = output_lines[1:]
    connected     = [line for line in device_lines if line.strip().endswith("\tdevice")]
    unauthorized  = [line for line in device_lines if line.strip().endswith("\tunauthorized")]
    offline       = [line for line in device_lines if line.strip().endswith("\toffline")]

    if unauthorized:
        log_callback("[ERREUR] Appareil non autorisé. Acceptez la clé RSA sur le téléphone.")
        return
    if offline:
        log_callback("[ERREUR] Appareil hors ligne. Redémarrez ADB ou reconnectez le câble.")
        return
    if not connected:
        log_callback("[ERREUR] Aucun appareil connecté (pas de statut 'device').")
        return

    # --- Lecture du dossier DCIM/Camera ---
    possible_paths = [
        "/sdcard/DCIM/Camera",
        "/storage/emulated/0/DCIM/Camera",
        "/sdcard/DCIM/100MEDIA",
        "/sdcard/DCIM/OpenCamera"
    ]

    remote_files = []
    for path in possible_paths:
        try:
            output = subprocess.check_output([ADB_PATH, "shell", "ls", path],
                                            startupinfo=startupinfo).decode("utf-8", errors="ignore")
            files = [f.strip() for f in output.splitlines() if f.strip()]
            if files:
                remote_files = files
                break
        except subprocess.CalledProcessError:
            continue  # Ignore paths that fail

    if not remote_files:
        return  # Aucun fichier trouvé, on quitte proprement

    total_files = len(remote_files)
    processed_files = 0
    downloaded_files = 0
    progress_callback(processed_files, total_files)

    existing_photos = _list_all_files(photos_path)
    existing_videos = _list_all_files(videos_path)

    for filename in remote_files:
        if cancel_flag.cancelled:
            log_callback("[INFO] Téléchargement interrompu par l'utilisateur.")
            break

        ext = os.path.splitext(filename)[1].lower()

        if ext == ".jpg" and not download_photos:
            log_callback(f"[IGNORÉ] Photos désactivées : {filename}")
            processed_files += 1
            progress_callback(processed_files, total_files)
            continue
        if ext == ".mp4" and not download_videos:
            log_callback(f"[IGNORÉ] Vidéos désactivées : {filename}")
            processed_files += 1
            progress_callback(processed_files, total_files)
            continue

        if ext == ".jpg" and filename in existing_photos:
            log_callback(f"[IGNORÉ] Photo déjà présente : {filename}")
        elif ext == ".mp4" and filename in existing_videos:
            log_callback(f"[IGNORÉ] Vidéo déjà présente : {filename}")
        elif ext in [".jpg", ".mp4"]:
            log_callback(f"[DL] Téléchargement : {filename}")
            try:
                subprocess.run([ADB_PATH, "pull", f"/sdcard/DCIM/Camera/{filename}",
                                os.path.join(save_path, filename)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               startupinfo=startupinfo)
                downloaded_files += 1
            except Exception as e:
                log_callback(f"[ERREUR] {filename} : {repr(e)}")
        else:
            log_callback(f"[IGNORÉ] Fichier non pris en charge : {filename}")

        processed_files += 1
        progress_callback(processed_files, total_files)
        time.sleep(0.1)

    log_callback(f"[FIN] {downloaded_files} fichier(s) téléchargé(s), "
                 f"{processed_files - downloaded_files} ignoré(s).")