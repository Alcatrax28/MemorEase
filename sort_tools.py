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
    seen = {}
    duplicates_removed = 0

    for f in files:
        if cancel_flag.cancelled:
            log_callback("Détection doublons interrompue.")
            break

        path = os.path.join(save_path, f)
        ext = os.path.splitext(f)[1].lower()

        if ext == ".jpg":
            h = image_hash(path)
            if h:
                duplicate = None
                for prev, prev_hash in seen.items():
                    log_callback(f"[COMPARE]\t{f} <-> {prev}")
                    # distance de Hamming <= 2 ≈ 98% similaire
                    if h - prev_hash <= 2:
                        duplicate = prev
                        break
                    # test rotations
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
                    seen[f] = h

        elif ext == ".mp4":
            h = file_md5(path)
            if h in seen.values():
                prev = [k for k, v in seen.items() if v == h][0]
                log_callback(f"[COMPARE]\t{f} <-> {prev}")
                to_delete = max(f, prev)
                os.remove(os.path.join(save_path, to_delete))
                duplicates_removed += 1
                log_callback(f"[DUPLICAT]\t{to_delete} supprimé (identique à {prev})")
            else:
                seen[f] = h

        processed += 1
        percent = int((processed / total) * 100) if total else 100
        progress_callback(percent)

    log_callback(f"[RÉSUMÉ]\t{duplicates_removed} doublons supprimés")

# -------------------------------
# Regex formats attendus
# -------------------------------

PHOTO_PATTERN = re.compile(r"^IMG(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(?:_(\d{2}))?\.jpg$", re.IGNORECASE)
VIDEO_PATTERN = re.compile(r"^VID(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(?:_(\d{2}))?\.mp4$", re.IGNORECASE)

# -------------------------------
# Dates
# -------------------------------

def _get_exif_datetime(path):
    """Retourne un datetime à partir des métadonnées EXIF si dispo."""
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
    """Retourne un datetime basé sur la date de création/modification du fichier."""
    try:
        ts = os.path.getmtime(path)
        return datetime.fromtimestamp(ts)
    except Exception:
        return None

# -------------------------------
# Normalisation nom
# -------------------------------

def _normalize_filename(filename, ext):
    """
    Force un format strict IMGYYYYMMDDHHMMSS.ext ou VIDYYYYMMDDHHMMSS.ext
    en supprimant tout suffixe parasite après la date/heure.
    """
    base, _ = os.path.splitext(filename)
    m = re.search(r'(\d{14})', base)
    if m:
        date_str = m.group(1)
        prefix = "IMG" if ext.lower() == ".jpg" else "VID"
        return f"{prefix}{date_str}{ext.lower()}"
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
                # Si le move échoue (ex. déjà déplacé), on logue quand même l'erreur
                pass
            error_occurred = True
            log_callback(f"[ERREUR]\t{filename} déplacé vers {err_path} ({e})")

        percent = int((moved_files / total_files) * 100) if total_files else 100
        progress_callback(percent)
        time.sleep(0.05)

    if not error_occurred and os.path.isdir(error_dir) and not os.listdir(error_dir):
        try:
            os.rmdir(error_dir)
        except OSError:
            pass

    log_callback("Tri et sauvegarde terminés.")