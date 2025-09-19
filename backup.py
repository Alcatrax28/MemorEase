import subprocess
import os
import re
import sys

def run_backup(photo_src, video_src, backup_dest,
               log_callback=None, progress_callback=None, cancel_flag=None):

    def count_files(path):
        total = 0
        for _, _, files in os.walk(path):
            total += len(files)
        return total

    # Calcul du total de fichiers à traiter
    total_files = count_files(photo_src) + count_files(video_src)
    done = 0

    def _run_single(src, subfolder):
        nonlocal done
        dest = os.path.join(backup_dest, "MemorEase_backup", subfolder)
        cmd = [
            "robocopy",
            src,
            dest,
            "/MIR",   # miroir
            "/NJH",   # pas d'entête
            "/NJS",   # pas de résumé
            "/NDL",   # pas de liste de dossiers
            "/NP",    # pas de progression en %
        ]

        # Empêcher l'ouverture d'une fenêtre console sous Windows
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=creationflags
        )

        for line in proc.stdout:
            if cancel_flag and cancel_flag.cancelled:
                proc.terminate()
                if log_callback:
                    log_callback(f"Backup interrompu sur {subfolder}")
                return False

            # Filtrer les lignes vides ou juste %
            if re.fullmatch(r"\s*\d+(\.\d+)?%\s*", line):
                continue

            # Détection d'un fichier copié/mis à jour
            if line.strip() and not line.startswith(" ") and not line.endswith("%"):
                done += 1
                if progress_callback:
                    progress_callback(done, total_files)

            if log_callback:
                log_callback(line.rstrip())

        return True

    # Lancer les deux backups
    _run_single(photo_src, "Photos")
    _run_single(video_src, "Videos")

    return not (cancel_flag and cancel_flag.cancelled), total_files