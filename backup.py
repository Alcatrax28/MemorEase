import os
import shutil
import hashlib

def md5sum(path, block_size=65536):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(block_size), b''):
            h.update(chunk)
    return h.hexdigest()

def run_backup(photo_src, video_src, backup_dest,
               log_callback=None, progress_callback=None, cancel_flag=None):

    def count_files(path):
        total = 0
        for _, _, files in os.walk(path):
            total += len(files)
        return total

    base_dest = os.path.join(backup_dest, "MemorEase_backup")
    photos_dst = os.path.join(base_dest, "Photos")
    videos_dst = os.path.join(base_dest, "Videos")

    src_count = count_files(photo_src) + count_files(video_src)
    dst_count = (count_files(photos_dst) if os.path.isdir(photos_dst) else 0) \
              + (count_files(videos_dst) if os.path.isdir(videos_dst) else 0)
    total = src_count + dst_count
    done = 0

    if progress_callback:
        progress_callback(0, total)

    # Largeur fixe pour aligner les colonnes
    name_col_width = 50

    def mirror(src_root, dst_root):
        nonlocal done

        src_files = {}
        for root, _, files in os.walk(src_root):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), src_root)
                src_files[rel] = os.path.join(root, f)

        dst_files = {}
        if os.path.isdir(dst_root):
            for root, _, files in os.walk(dst_root):
                for f in files:
                    rel = os.path.relpath(os.path.join(root, f), dst_root)
                    dst_files[rel] = os.path.join(root, f)

        os.makedirs(dst_root, exist_ok=True)

        for rel, src_path in src_files.items():
            if cancel_flag and cancel_flag.cancelled:
                if log_callback:
                    log_callback("[STOP] Le backup a été interrompu par l'utilisateur.")
                return False

            dst_path = os.path.join(dst_root, rel)
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)

            if rel in dst_files:
                try:
                    same = md5sum(src_path) == md5sum(dst_path)
                except FileNotFoundError:
                    same = False
                if same:
                    done += 2
                    if progress_callback:
                        progress_callback(done, total)
                    if log_callback:
                        log_callback(f"[IGNORÉ]\t{rel.ljust(name_col_width)}\t déjà présent")
                    continue

            shutil.copy2(src_path, dst_path)
            done += 1
            if progress_callback:
                progress_callback(done, total)
            if log_callback:
                log_callback(f"[COPIÉ]\t{rel.ljust(name_col_width)}")

        for rel, dst_path in dst_files.items():
            if cancel_flag and cancel_flag.cancelled:
                if log_callback:
                    log_callback("[STOP] Le backup a été interrompu par l'utilisateur.")
                return False
            if rel not in src_files:
                try:
                    os.remove(dst_path)
                except FileNotFoundError:
                    pass
                done += 1
                if progress_callback:
                    progress_callback(done, total)
                if log_callback:
                    log_callback(f"[SUPPRIMÉ]\t{rel.ljust(name_col_width)}\t absent du dossier source")

        return True

    ok1 = mirror(photo_src, photos_dst)
    if not ok1:
        return False, done, total
    ok2 = mirror(video_src, videos_dst)
    if not ok2:
        return False, done, total

    success = ok1 and ok2 and not (cancel_flag and cancel_flag.cancelled)
    return success, done, total