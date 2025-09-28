import os
import re
import shutil
import imagehash                        # pyright: ignore[reportMissingImports]
from datetime import datetime
from PIL import Image                   # pyright: ignore[reportMissingImports]
from PIL.ExifTags import TAGS           # pyright: ignore[reportMissingImports]
from utils import file_md5

# -------------------------------
# Formatage des logs
# -------------------------------
def format_log(code, action, target=""):
    code_str = f"[{code}]"
    # largeur fixe pour la colonne code
    code_col = code_str.ljust(10)
    if target:
        return f"{code_col}{action}\t-> {target}"
    else:
        return f"{code_col}{action}"

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

    m = re.search(r'(\d{14})', base)
    if m:
        return f"{prefix}{m.group(1)}{ext}"

    m = re.search(r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})', base)
    if m:
        date_str = f"{m.group(1)}{m.group(2)}{m.group(3)}{m.group(4)}{m.group(5)}"
        return f"{prefix}{date_str}{ext}"

    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', base)
    if m:
        date_key = f"{prefix}{m.group(1)}{m.group(2)}{m.group(3)}"
        existing = [f for f in os.listdir(os.path.dirname(os.path.abspath(__file__)))
                    if f.startswith(date_key + "_N") and f.endswith(ext)]
        count = len(existing) + 1
        suffix = f"_N{count:04d}"
        return f"{date_key}{suffix}{ext}"

    return filename

# -------------------------------
# Fonction principale
# -------------------------------
def process_files_individually(save_path, photos_path, videos_path, log_callback, progress_callback, cancel_flag):
    if not os.path.isdir(save_path):
        log_callback(format_log("ERREUR", "Dossier de sauvegarde introuvable", save_path))
        return

    files = sorted([f for f in os.listdir(save_path) if os.path.isfile(os.path.join(save_path, f))])
    total_files = len(files)
    total_ops = total_files * 3
    done_ops = 0

    log_callback(format_log("INFO", "Étape 1 : Renommage des fichiers..."))
    renamed_files = []
    for f in files:
        if cancel_flag.cancelled:
            log_callback(format_log("STOP", "Opération interrompue par l'utilisateur"))
            return
        ext = os.path.splitext(f)[1].lower()
        new_name = _normalize_filename(f, ext)
        if new_name != f:
            try:
                os.rename(os.path.join(save_path, f), os.path.join(save_path, new_name))
                log_callback(format_log("RENAMED", f, new_name))
                renamed_files.append(new_name)
            except Exception as e:
                log_callback(format_log("ERREUR", f"Impossible de renommer {f}", str(e)))
                renamed_files.append(f)
        else:
            log_callback(format_log("OK", f))
            renamed_files.append(f)

        done_ops += 1
        progress_callback(int(done_ops / total_ops * 100))

    log_callback(format_log("INFO", "Étape 2 : Détection doublons et déplacement..."))
    seen_images = {}
    seen_videos = {}
    error_dir = os.path.join(save_path, "Erreur_tri")
    os.makedirs(error_dir, exist_ok=True)

    for filename in sorted(renamed_files):
        if cancel_flag.cancelled:
            log_callback(format_log("STOP", "Opération interrompue par l'utilisateur"))
            break

        path = os.path.join(save_path, filename)
        if not os.path.exists(path):
            done_ops += 2
            progress_callback(int(done_ops / total_ops * 100))
            continue

        ext = os.path.splitext(filename)[1].lower()
        log_callback(format_log("SEARCH", f"recherche de doublons pour {filename}"))

        is_duplicate = False
        duplicate_of = None

        if ext == ".jpg":
            try:
                img = Image.open(path).convert("RGB")
                h = imagehash.phash(img)
                hash_size = h.hash.size

                def is_similar(h1, h2):
                    distance = h1 - h2
                    similarity = 1 - (distance / hash_size)
                    return similarity >= 0.98

                for prev, prev_hash in seen_images.items():
                    if is_similar(h, prev_hash):
                        is_duplicate = True
                        duplicate_of = prev
                        break
                    for angle in (90, 180, 270):
                        rotated_hash = imagehash.phash(img.rotate(angle, expand=True))
                        if is_similar(rotated_hash, prev_hash):
                            is_duplicate = True
                            duplicate_of = prev
                            break
                    if is_duplicate:
                        break

                if is_duplicate:
                    os.remove(path)
                    log_callback(format_log("DUPLICAT", f"{filename} supprimé", f"similaire à {duplicate_of}"))
                else:
                    seen_images[filename] = h

            except Exception as e:
                log_callback(format_log("ERREUR", f"Impossible d’analyser {filename}", str(e)))

        elif ext == ".mp4":
            h = file_md5(path)
            if h in seen_videos.values():
                duplicate_of = [k for k, v in seen_videos.items() if v == h][0]
                os.remove(path)
                log_callback(format_log("DUPLICAT", f"{filename} supprimé", f"identique à {duplicate_of}"))
                is_duplicate = True
            else:
                seen_videos[filename] = h

        done_ops += 1
        progress_callback(int(done_ops / total_ops * 100))

        if is_duplicate:
            done_ops += 1
            progress_callback(int(done_ops / total_ops * 100))
            continue

        try:
            match_photo = PHOTO_PATTERN.match(filename)
            match_video = VIDEO_PATTERN.match(filename)

            if match_photo:
                year = match_photo.group(1)
                dest_dir = os.path.join(photos_path, year)
            elif match_video:
                year = match_video.group(1)
                dest_dir = os.path.join(videos_path, year)
            elif ext in (".jpg", ".mp4"):
                dt = _get_exif_datetime(path) if ext == ".jpg" else _get_file_datetime(path)
                prefix = "IMG" if ext == ".jpg" else "VID"
                if dt:
                    filename = f"{prefix}{dt.strftime('%Y%m%d%H%M%S')}{ext}"
                    year = dt.strftime("%Y")
                    dest_dir = os.path.join(photos_path if ext == ".jpg" else videos_path, year)
                else:
                    dest_dir = error_dir
                    log_callback(format_log("ERREUR", f"{filename} déplacé vers Erreur_tri", "pas de date"))
            else:
                log_callback(format_log("IGNORÉ", filename, "extension non prise en charge"))
                done_ops += 1
                progress_callback(int(done_ops / total_ops * 100))
                continue

            os.makedirs(dest_dir, exist_ok=True)
            final_path = os.path.join(dest_dir, filename)
            shutil.move(path, final_path)
            log_callback(format_log("MOVE", f"{filename} déplacé", final_path))

        except Exception as e:
            err_path = os.path.join(error_dir, filename)
            try:
                shutil.move(path, err_path)
                log_callback(format_log("ERREUR", f"{filename} déplacé vers Erreur_tri", str(e)))
            except Exception as move_error:
                log_callback(format_log("ERREUR", f"Échec déplacement de {filename}", str(move_error)))

        done_ops += 1
        progress_callback(int(done_ops / total_ops * 100))

    # Fin de boucle fichiers
    progress_callback(100)
    log_callback(format_log("FIN", "Traitement terminé"))