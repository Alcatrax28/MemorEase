import os
import re
import shutil
import time
import imagehash                        # pyright: ignore[reportMissingImports]
from datetime import datetime
from PIL import Image                   # pyright: ignore[reportMissingImports]
from PIL.ExifTags import TAGS           # pyright: ignore[reportMissingImports]
from utils import file_md5, image_hash

# -------------------------------
# Détection doublons
# -------------------------------

def _remove_duplicates(save_path, log_callback, progress_callback, cancel_flag):
    files = sorted([f for f in os.listdir(save_path) if os.path.isfile(os.path.join(save_path, f))])
    total = len(files)
    processed = 0
    seen_images = {}
    seen_videos = {}
    duplicates_removed = 0

    for f in files:
        if cancel_flag.cancelled:
            log_callback("Détection doublons interrompue.")
            progress_callback(100)
            break

        path = os.path.join(save_path, f)
        ext = os.path.splitext(f)[1].lower()

        if ext == ".jpg":
            h = image_hash(path)
            if h:
                duplicate = None
                for prev, prev_hash in seen_images.items():
                    log_callback(f"[COMPARE]\t{f} <-> {prev}")
                    if h - prev_hash <= 2:
                        duplicate = prev
                        break
                    try:
                        img = Image.open(path).convert("RGB")
                        for angle in (90, 180, 270):
                            if imagehash.phash(img.rotate(angle, expand=True)) - prev_hash <= 2:
                                duplicate = prev
                                break
                    except Exception:
                        pass
                if duplicate:
                    to_delete = max(f, duplicate)
                    os.remove(os.path.join(save_path, to_delete))
                    duplicates_removed += 1
                    log_callback(f"[DUPLICAT]\t{to_delete} supprimé (similaire à {duplicate})")
                else:
                    seen_images[f] = h

        elif ext == ".mp4":
            h = file_md5(path)
            if h in seen_videos.values():
                prev = [k for k, v in seen_videos.items() if v == h][0]
                log_callback(f"[COMPARE]\t{f} <-> {prev}")
                to_delete = max(f, prev)
                os.remove(os.path.join(save_path, to_delete))
                duplicates_removed += 1
                log_callback(f"[DUPLICAT]\t{to_delete} supprimé (identique à {prev})")
            else:
                seen_videos[f] = h

        processed += 1
        percent = int((processed / total) * 100) if total else 100
        progress_callback(percent)

    log_callback(f"[RÉSUMÉ]\t{duplicates_removed} doublons supprimés")
    progress_callback(100)

# -------------------------------
# Regex formats attendus
# -------------------------------

PHOTO_PATTERN = re.compile(r"^IMG(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(?:_(\d{2}))?\.jpg$", re.IGNORECASE)
VIDEO_PATTERN = re.compile(r"^VID(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(?:_(\d{2}))?\.mp4$", re.IGNORECASE)

# -------------------------------
# Dates
# -------------------------------

def _get_exif_datetime(path):
    try:
        img = Image.open(path)
        exif_data = img._getexif()
        if not exif_data:
            return None
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag in ("DateTimeOriginal", "DateTime"):
                try:
                    return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                except Exception:
                    return None
    except Exception:
        return None
    return None

def _get_file_datetime(path):
    try:
        ts = os.path.getmtime(path)
        return datetime.fromtimestamp(ts)
    except Exception:
        return None

# -------------------------------
# Normalisation nom
# -------------------------------

def _normalize_filename(filename, ext):
    base, _ = os.path.splitext(filename)
    ext = ext.lower()
    prefix = "IMG" if ext == ".jpg" else "VID"

    # Cas 1 : format déjà correct (14 chiffres)
    m = re.search(r'(\d{14})', base)
    if m:
        return f"{prefix}{m.group(1)}{ext}"

    # Cas 2 : format type IMG_2024-09-13_23-59
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})', base)
    if m:
        date_str = f"{m.group(1)}{m.group(2)}{m.group(3)}{m.group(4)}{m.group(5)}"
        return f"{prefix}{date_str}{ext}"

    # Cas 3 : format type IMG_2024-09-13 (sans heure)
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', base)
    if m:
        date_key = f"{prefix}{m.group(1)}{m.group(2)}{m.group(3)}"
        # Compteur basé sur les fichiers déjà présents dans le dossier
        existing = [f for f in os.listdir(os.path.dirname(os.path.abspath(__file__)))
                    if f.startswith(date_key + "_N") and f.endswith(ext)]
        count = len(existing) + 1
        suffix = f"_N{count:04d}"
        return f"{date_key}{suffix}{ext}"

    # Cas non reconnu : on garde le nom original
    return filename

# -------------------------------
# Fonction principale
# -------------------------------

def sort_and_save_files(save_path, photos_path, videos_path, log_callback, progress_callback, cancel_flag):
    if not os.path.isdir(save_path):
        log_callback(f"Dossier de sauvegarde introuvable : {save_path}")
        return

    # Phase 1 : Renommage
    log_callback("Phase 1 : Renommage des fichiers...")
    files = sorted([f for f in os.listdir(save_path) if os.path.isfile(os.path.join(save_path, f))])
    total_rename = len(files)
    processed_rename = 0
    for f in files:
        if cancel_flag.cancelled:
            log_callback("Opération interrompue par l'utilisateur.")
            return
        path = os.path.join(save_path, f)
        ext = os.path.splitext(f)[1].lower()
        new_name = _normalize_filename(f, ext)
        if new_name != f:
            try:
                os.rename(path, os.path.join(save_path, new_name))
                log_callback(f"[RENAMED]\t{f} -> {new_name}")
            except Exception as e:
                log_callback(f"[ERREUR]\tImpossible de renommer {f} ({e})")
        else:
            log_callback(f"[OK]\t{f}")
        processed_rename += 1
        percent = int((processed_rename / total_rename) * 100) if total_rename else 100
        progress_callback(percent)
    progress_callback(100)

    # Phase 2 : Suppression doublons
    log_callback("Phase 2 : Vérification des doublons...")
    _remove_duplicates(save_path, log_callback, progress_callback, cancel_flag)

    # Phase 3 : Tri et déplacement
    log_callback("Phase 3 : Tri et déplacement...")
    files = sorted([f for f in os.listdir(save_path) if os.path.isfile(os.path.join(save_path, f))])
    total_files = len(files)
    moved_files = 0
    error_dir = os.path.join(save_path, "Erreur_tri")
    error_occurred = False

    for filename in files:
        if cancel_flag.cancelled:
            log_callback("Opération interrompue par l'utilisateur.")
            break

        src = os.path.join(save_path, filename)
        ext = os.path.splitext(filename)[1].lower()

        match_photo = PHOTO_PATTERN.match(filename)
        match_video = VIDEO_PATTERN.match(filename)

        try:
            if match_photo:
                year = match_photo.group(1)
                dest_dir = os.path.join(photos_path, year)
                os.makedirs(dest_dir, exist_ok=True)
                shutil.move(src, os.path.join(dest_dir, filename))
                moved_files += 1
                log_callback(f"[MOVE]\t{filename} -> {os.path.join(dest_dir, filename)}")

            elif match_video:
                year = match_video.group(1)
                dest_dir = os.path.join(videos_path, year)
                os.makedirs(dest_dir, exist_ok=True)
                shutil.move(src, os.path.join(dest_dir, filename))
                moved_files += 1
                log_callback(f"[MOVE]\t{filename} -> {os.path.join(dest_dir, filename)}")

            elif ext in (".jpg", ".mp4"):
                if ext == ".jpg":
                    dt = _get_exif_datetime(src) or _get_file_datetime(src)
                    prefix = "IMG"
                else:
                    dt = _get_file_datetime(src)
                    prefix = "VID"

                if dt:
                    new_name = f"{prefix}{dt.strftime('%Y%m%d%H%M%S')}{ext.lower()}"
                    year = dt.strftime("%Y")
                    dest_dir = os.path.join(photos_path if ext == ".jpg" else videos_path, year)
                    os.makedirs(dest_dir, exist_ok=True)
                    final_path = os.path.join(dest_dir, new_name)
                    shutil.move(src, final_path)
                    moved_files += 1
                    log_callback(f"[MOVE]\t{filename} -> {final_path}")
                else:
                    os.makedirs(error_dir, exist_ok=True)
                    err_path = os.path.join(error_dir, filename)
                    shutil.move(src, err_path)
                    error_occurred = True
                    log_callback(f"[ERREUR]\t{filename} déplacé vers {err_path} (pas de date)")

            else:
                log_callback(f"[IGNORÉ]\t{filename} (extension non prise en charge)")

        except Exception as e:
            os.makedirs(error_dir, exist_ok=True)
            err_path = os.path.join(error_dir, filename)
            try:
                shutil.move(src, err_path)
            except Exception:
                pass
            error_occurred = True