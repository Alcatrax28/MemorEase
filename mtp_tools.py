import os
import glob
import shutil
import subprocess


def _list_all_files(root_dir):
    all_files = set()
    if os.path.isdir(root_dir):
        for dirpath, _, filenames in os.walk(root_dir):
            for f in filenames:
                all_files.add(f)
    return all_files


def _find_mtp_dcim(log_callback):
    """
    Cherche le dossier DCIM/Camera sur un appareil Android monté via MTP (GVFS).
    Tente un montage automatique via gio si l'appareil n'est pas encore monté.
    """
    gvfs_base = f"/run/user/{os.getuid()}/gvfs"

    dcim_suffixes = [
        "DCIM/Camera",
        "Internal storage/DCIM/Camera",
        "Stockage interne/DCIM/Camera",
        "Phone/DCIM/Camera",
        "SD card/DCIM/Camera",
        "Carte SD/DCIM/Camera",
    ]

    def _scan():
        if not os.path.isdir(gvfs_base):
            return None
        for mount in glob.glob(os.path.join(gvfs_base, "mtp:*")):
            for suffix in dcim_suffixes:
                dcim_path = os.path.join(mount, suffix)
                if os.path.isdir(dcim_path):
                    return dcim_path
        return None

    result = _scan()
    if result:
        return result

    # Tentative de montage automatique via gio
    log_callback("[INFO] Tentative de montage automatique de l'appareil...")
    try:
        r = subprocess.run(["gio", "mount", "-li"],
                           capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.startswith("mtp://"):
                subprocess.run(["gio", "mount", line],
                               capture_output=True, timeout=15)
                break
    except Exception:
        pass

    return _scan()


def run_mtp_download(save_path, photos_path, videos_path,
                     log_callback, progress_callback, cancel_flag,
                     download_photos=True, download_videos=True):

    PHOTO_EXTS = {".jpg", ".jpeg", ".png"}
    VIDEO_EXTS = {".mp4", ".mov"}

    log_callback("[INFO] Recherche d'un appareil MTP monté...")
    dcim_path = _find_mtp_dcim(log_callback)

    if not dcim_path:
        log_callback("[ERREUR] Aucun appareil MTP trouvé.")
        log_callback("[INFO] Branchez le téléphone en mode 'Transfert de fichiers',")
        log_callback("[INFO] puis ouvrez le gestionnaire de fichiers pour le monter.")
        return

    log_callback(f"[OK] DCIM trouvé : {dcim_path}")
    os.makedirs(save_path, exist_ok=True)

    try:
        all_entries = os.listdir(dcim_path)
        remote_files = [f for f in all_entries
                        if os.path.isfile(os.path.join(dcim_path, f))]
    except Exception as e:
        log_callback(f"[ERREUR] Impossible de lire DCIM : {repr(e)}")
        return

    total_files = len(remote_files)
    if total_files == 0:
        log_callback("[INFO] Aucun fichier trouvé dans DCIM/Camera.")
        return

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

        if ext in PHOTO_EXTS and not download_photos:
            log_callback(f"[IGNORÉ] Photos désactivées : {filename}")
            processed_files += 1
            progress_callback(processed_files, total_files)
            continue

        if ext in VIDEO_EXTS and not download_videos:
            log_callback(f"[IGNORÉ] Vidéos désactivées : {filename}")
            processed_files += 1
            progress_callback(processed_files, total_files)
            continue

        if ext in PHOTO_EXTS and filename in existing_photos:
            log_callback(f"[IGNORÉ] Photo déjà présente : {filename}")
        elif ext in VIDEO_EXTS and filename in existing_videos:
            log_callback(f"[IGNORÉ] Vidéo déjà présente : {filename}")
        elif ext in PHOTO_EXTS | VIDEO_EXTS:
            log_callback(f"[COPIE] {filename}")
            try:
                src = os.path.join(dcim_path, filename)
                dst = os.path.join(save_path, filename)
                shutil.copy2(src, dst)
                downloaded_files += 1
            except Exception as e:
                log_callback(f"[ERREUR] {filename} : {repr(e)}")
        else:
            log_callback(f"[IGNORÉ] Extension non prise en charge : {filename}")

        processed_files += 1
        progress_callback(processed_files, total_files)

    log_callback(f"[FIN] {downloaded_files} fichier(s) copié(s), "
                 f"{processed_files - downloaded_files} ignoré(s).")
