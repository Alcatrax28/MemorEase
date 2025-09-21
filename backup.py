import subprocess
import os
import re

def run_backup(photo_src, video_src, backup_dest,
               log_callback=None, progress_callback=None, cancel_flag=None):
    
    done = 0    # Fichiers réellement copiés ou mis à jour

    def _run_single(src, subfolder):
        nonlocal done
        dest = os.path.join(backup_dest, "MemorEase_backup", subfolder)
        cmd = [
            "robocopy",
            src,
            dest,
            "/MIR",     # copie miroir
            "/NJH",     # pas d'entête
            "/NDL",     # pas de liste de dossiers (fichiers uniquement)
            "/NP",      # pas de progression en %
            "/ETA",
        ]

        creationflags = 0

        # Empêcher la création de fenêtre de commande Windows
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",           # Essayer "mbcs" si "utf-8" ne fonctionne pas correctement

            creationflags=creationflags
        )

        for line in proc.stdout:
            if cancel_flag and cancel_flag.cancelled:
                proc.terminate()
                if log_callback:
                    log_callback(f"⛔ Backup interrompu sur {subfolder}")
                return False
            
            line = line.expandtabs().rstrip()

            # Détection d'un fichier copié ou mis à jour
            if re.search(r"\s+\d+\s+.*", line):     # Ligne contenant un compteur
                done += 1

                if progress_callback:
                    progress_callback(done, None)   # total inconnu -> on affiche uniquement le compteur

            if log_callback:
                log_callback(line)

        return True
    
    # Lancer les deux backups
    _run_single(photo_src, "Photos")
    _run_single(video_src, "Videos")

    return not (cancel_flag and cancel_flag.cancelled), done