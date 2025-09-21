import subprocess
import os
import re

def run_backup(photo_src, video_src, backup_dest,
               log_callback=None, progress_callback=None, cancel_flag=None):

    # 1) Total à traiter (tous les fichiers sources)
    def count_files(path):
        total = 0
        for _, _, files in os.walk(path):
            total += len(files)
        return total

    total_files = count_files(photo_src) + count_files(video_src)
    done = 0

    # Lignes "fichier" typiques: "2025/09/21 22:03:17 123456 E:\path\file.ext"
    FILE_LINE_RE = re.compile(
    r"^\s*(Nouveau fichier|Fichier\s+plus\s+récent|Fichier\s+identique|Nouveau\s+dossier)\s+\d+\s+.+$",
    re.IGNORECASE
)


    def _run_single(src, subfolder):
        nonlocal done
        dest = os.path.join(backup_dest, "MemorEase_backup", subfolder)
        cmd = [
            "robocopy",
            src,
            dest,
            "/MIR",   # miroir
            "/E",     # inclut sous-dossiers vides (ou /S si tu préfères ignorer vides)
            "/NJH",   # pas d'en-tête
            "/NP",    # pas de progression %
            "/NDL",   # ne liste pas les dossiers (évite le faux comptage)
            "/BYTES", # taille en bytes (colonne taille toujours numérique)
            # Optionnel pour éviter de bloquer sur fichiers verrouillés:
            "/R:0",   # 0 retry
            "/W:0",   # 0 seconde d'attente
        ]

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        encoding = "mbcs" if os.name == "nt" else "utf-8"

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding=encoding,
            creationflags=creationflags
        )

        for raw in proc.stdout:
            if cancel_flag and cancel_flag.cancelled:
                proc.terminate()
                if log_callback:
                    log_callback(f"⛔ Backup interrompu ({subfolder})")
                return False

            line = raw.expandtabs().rstrip()

            # Incrémenter pour chaque ligne fichier détectée
            if FILE_LINE_RE.match(line):
                done += 1
                if progress_callback:
                    progress_callback(done, total_files)

            if log_callback:
                log_callback(line)

        return True

    # 2) Exécuter les deux passes
    _run_single(photo_src, "Photos")
    _run_single(video_src, "Videos")

    # 3) Ajustement final si la destination contient déjà tout
    photos_dst = os.path.join(backup_dest, "MemorEase_backup", "Photos")
    videos_dst = os.path.join(backup_dest, "MemorEase_backup", "Videos")
    dest_total = count_files(photos_dst) + count_files(videos_dst)

    if dest_total >= total_files:
        done = total_files
        if progress_callback:
            progress_callback(done, total_files)

    return not (cancel_flag and cancel_flag.cancelled), done, total_files