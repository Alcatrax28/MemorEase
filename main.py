import customtkinter as ctk # pyright: ignore[reportMissingImports]
import tkinter as tk
from tkinter import filedialog, scrolledtext
import os
import json
import getpass
import string
import threading
from CTkMessagebox import CTkMessagebox # pyright: ignore[reportMissingImports]
from adb_tools import run_adb_download
from sort_tools import sort_and_save_files
from backup import run_backup
from spinner_widget import SpinnerWidget
from update_maker import check_for_update, download_update, launch_new_version # pyright: ignore[reportMissingImports]
from utils import resource_path, CONFIG_FILE, VERSION_FILE # pyright: ignore[reportMissingImports]

def read_version():
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""

def find_onedrive():
    for drive in (f"{d}:\\" for d in string.ascii_uppercase):
        users_dir = os.path.join(drive, "Users")
        if not os.path.isdir(users_dir):
            continue
        # Parcourir chaque profil utilisateur
        for user_folder in os.listdir(users_dir):
            base = os.path.join(users_dir, user_folder)
            if not os.path.isdir(base):
                continue
            # Chercher OneDrive / Onedrive dans ce profil
            for name in ("OneDrive", "Onedrive", "onedrive"):
                path = os.path.join(base, name)
                if os.path.isdir(path):
                    return path
    return None

def get_default_paths():
    od = find_onedrive()
    user = getpass.getuser()
    if od:
        save   = os.path.join(od, "Images", "Memorease_Downloads")
        photos = os.path.join(od, "Images", "Photos")
        videos = os.path.join(od, "Videos", "Mes videos")
    else:
        root_drive = os.getcwd().split(os.sep)[0] + "\\"
        base       = os.path.join(root_drive, "Users", user)
        save   = os.path.join(base, "Pictures", "Memorease_Downloads")
        photos = os.path.join(base, "Pictures", "Photos")
        videos = os.path.join(base, "Videos", "Mes videos")
    return save, photos, videos

class ModalWindow(ctk.CTkToplevel):
    def __init__(self, master, title="Fenêtre", size="600x400", icon_path=None):
        super().__init__(master)
        self.title(title)
        self.geometry(size)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.focus_force()
        self.lift()

        if icon_path:
            self.iconbitmap(icon_path)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Unmap>", lambda e: self.after(100, self._restore_if_minimized))

    def _restore_if_minimized(self):
        if self.state() == "iconic":
            self.deiconify()
            self.lift()
            self.focus_force()

    def _on_close(self):
        self.grab_release()
        self.destroy()

class CancelFlag:
    def __init__(self):
        self.cancelled = False

class UpdateWindow(ctk.CTkToplevel):
    def __init__(self, master, update_info):
        super().__init__(master)
        self.title("Mise à jour en cours")
        self.geometry("900x500")
        ico_path = os.path.abspath(resource_path("icon.ico"))
        self.iconbitmap(ico_path)


        # Rendre la fenêtre modale
        self.transient(master)
        self.grab_set()
        self.focus_force()

        self.update_info = update_info
        self.cancel_flag = CancelFlag()

        self._create_widgets()
        threading.Thread(target=self._start_update, daemon=True).start()

    def _create_widgets(self):
        self.progress_label = ctk.CTkLabel(self, text="Progression : 0 %")
        self.progress_label.pack(pady=(20, 5))

        self.progressbar = ctk.CTkProgressBar(self, width=700)
        self.progressbar.set(0)
        self.progressbar.pack(pady=10)

        self.console = scrolledtext.ScrolledText(
            self, height=18, state="disabled",
            font=("IBM Plex Mono", 10), wrap="none"
        )
        self.console.pack(pady=10, fill="both", expand=True)

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=10)

        self.cancel_button = ctk.CTkButton(
            btn_frame, text="Annuler", command=self._request_cancel, fg_color="red"
        )
        self.cancel_button.grid(row=0, column=0, padx=10)

        self.finish_button = ctk.CTkButton(
            btn_frame, text="Terminer", command=self.destroy, state="disabled"
        )
        self.finish_button.grid(row=0, column=1, padx=10)

    def _log(self, message):
        self.console.configure(state="normal")
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)
        self.console.configure(state="disabled")

    def _update_progress(self, done, total):
        if total == 0:
            self.progressbar.set(0)
            self.progress_label.configure(text="Progression : 0 %")
        else:
            ratio = done / total
            self.progressbar.set(ratio)
            self.progress_label.configure(text=f"Progression : {int(ratio*100)} %")

    def _request_cancel(self):
        self.cancel_flag.cancelled = True
        self._log("Annulation demandée...")

    def _start_update(self):
        temp_path = download_update(
            self.update_info["url"],
            log_callback=lambda msg: self.after(0, self._log, msg),
            progress_callback=lambda d, t: self.after(0, self._update_progress, d, t),
            cancel_flag=self.cancel_flag
        )
        if temp_path:
            self._log("Mise à jour téléchargée.")
            launch_new_version(temp_path, log_callback=lambda msg: self.after(0, self._log, msg))
        else:
            self._log("Mise à jour annulée ou échouée.")
        self.finish_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.download_photos = ctk.BooleanVar(value=True)
        self.download_videos = ctk.BooleanVar(value=True)
        self.secondary_window = None

        self._create_menu()
        self._create_main_widgets()
        self._create_footer()

        # Définition de la police personnalisée IBM Plex Mono

        default_font = ctk.CTkFont(family="IBM Plex Mono", size=12)
        self.option_add("*Font", default_font)

        version = self._load_version()
        title   = f"MemorEase" + (f" v{version}" if version else "")
        self.title(title)
        self.geometry("400x300")
        self.resizable(False, False)
   
    def _open_settings(self):
        if self.secondary_window is None or not tk.Toplevel.winfo_exists(self.secondary_window):
            self.secondary_window = SettingsADBWindow(
                self,
                download_photos=self.download_photos.get(),
                download_videos=self.download_videos.get()
            )
        else:
            self.secondary_window.deiconify()
            self.secondary_window.lift()
            self.secondary_window.focus_force()
            self.secondary_window.grab_set()
            ico_path = os.path.abspath(resource_path("icon.ico"))
            self.iconbitmap(ico_path)
    
    def _load_version(self):
        try:
            with open(resource_path("assets/version.txt"), "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            print("Erreur lecture version.txt :", e)
            return "inconnue" 

    def _create_footer(self):
        version_text = f"Version actuelle : {self._load_version()}"
        footer_label = ctk.CTkLabel(
            self,
            text=version_text,
            text_color="#A0A0A0",
            font=("IBM Plex Mono", 10)
        )
        footer_label.pack(side="left", anchor="sw", padx=10, pady=5)

    # Menu header
    def _create_menu(self):
        menubar   = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)

        # Fichiers > Quitter
        file_menu.add_command(label="Quitter", command=self.quit)
        menubar.add_cascade(label="Fichiers", menu=file_menu)

        # Aide > Changelog
        options_menu = tk.Menu(menubar, tearoff=0)
        options_menu.add_command(label="Changelog", command=self._open_changelog)
        options_menu.add_command(label="Vérifier les mises à jour", command=self.handle_update_if_needed)
        menubar.add_cascade(label="Options", menu=options_menu)

        self.config(menu=menubar)

    def _create_main_widgets(self):

        # Définition de la police personnalisée "IBM Logo"
        logo_font = ctk.CTkFont(family="IBM Logo", size=24)
        self.label = ctk.CTkLabel(self, text="MemorEase", font=logo_font)
        self.label.pack(pady=20)

        self.cb_photos = ctk.CTkCheckBox(self, text="Télécharger les photos",
                                         variable=self.download_photos,
                                         border_width=2,
                                         command=self._update_state)
        self.cb_photos.pack(pady=5)

        self.cb_videos = ctk.CTkCheckBox(self, text="Télécharger les vidéos",
                                         variable=self.download_videos,
                                         border_width=2,
                                         command=self._update_state)
        self.cb_videos.pack(pady=5)

        self.adb_button = ctk.CTkButton(self,
                                          text="Commencer la sauvegarde",
                                          command=self._open_settings)
        self.adb_button.pack(pady=10)

        self.sort_button = ctk.CTkButton(self, text="Trier et sauvegarder les fichiers téléchargés",
                                         command=lambda: SettingsSortWindow(self))
        self.sort_button.pack(pady=10)

        self.backup_button = ctk.CTkButton(self,
                                           text="Réaliser un backup vers un périphérique externe",
                                           command=self._open_backup_settings)
        self.backup_button.pack(pady=10)

        self._update_state()

    def _update_state(self):
        both_false = (not self.download_photos.get()
                      and not self.download_videos.get())
        color = "red" if both_false else "#a3a3a3"
        self.cb_photos.configure(border_color=color)
        self.cb_videos.configure(border_color=color)
        state = "disabled" if both_false else "normal"
        self.adb_button.configure(state=state)

    def _open_changelog(self):
        ChangelogWindow(self)

    def _open_backup_settings(self):
        SettingsBackupWindow(self)

    def open_modal(self, window_class, *args, **kwargs):
        if self.secondary_window is None or not tk.Toplevel.winfo_exists(self.secondary_window):
            self.secondary_window = window_class(self, *args, **kwargs)
        else:
            try:
                self.secondary_window.lift()
                self.secondary_window.focus_set()
            except Exception as e:
                print(f"[ERREUR] Impossible de restaurer la fenêtre secondaire : {e}")

    def handle_update_if_needed(self):
        update_info, local_version, remote_version = check_for_update()

        if remote_version is None:
            CTkMessagebox(
                title="Mise à jour",
                message="Impossible de vérifier les mises à jour (connexion ou fichier indisponible).",
                icon="warning"
            )
            return

        if not update_info:
            CTkMessagebox(
                title="Mise à jour",
                message=f"Version actuelle : {local_version}\nVersion disponible : {remote_version}\n\nMemorEase est à jour.",
                icon="info"
            )
            return

        msg = CTkMessagebox(
            title="Mise à jour disponible",
            message=(
                f"Version actuelle : {local_version}\n"
                f"Version disponible : {update_info['new_version']}\n\n"
                "Souhaitez-vous télécharger et installer la mise à jour ?"
            ),
            icon="info",
            option_1="Télécharger maintenant",
            option_2="Ignorer"
        )

        if msg.get() == "Télécharger maintenant":
            win = UpdateWindow(self, update_info)
            win.wait_window()

class SettingsADBWindow(ModalWindow):
    def __init__(self, master, download_photos=True, download_videos=True):
        super().__init__(master, title="Paramètres de sauvegarde", size="750x400", icon_path="icon.ico")
        
        self.download_photos = download_photos
        self.download_videos = download_videos

        self._load_config()
        self._create_widgets()
   
    def _load_config(self):
        # Toujours utiliser resource_path pour être compatible .py et .exe
        config_path = resource_path(os.path.join("assets", "config.json"))
        self.paths = None

        if os.path.isfile(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                save   = data.get("save")
                photos = data.get("photos")
                videos = data.get("videos")

                if all(isinstance(p, str) and p for p in (save, photos, videos)):
                    self.paths = (save, photos, videos)
            except (json.JSONDecodeError, IOError) as e:
                print(f"[ERREUR] Impossible de lire config.json : {e}")
                self.paths = None
        else:
            print(f"[ERREUR] Fichier introuvable : {config_path}")

    def _create_widgets(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Configuration des colonnes pour que la colonne 1 (Entry) s'étire
        frame.grid_columnconfigure(0, weight=0)  # Label
        frame.grid_columnconfigure(1, weight=1)  # Entry
        frame.grid_columnconfigure(2, weight=0)  # Bouton

        self.save_var   = tk.StringVar()
        self.photos_var = tk.StringVar()
        self.videos_var = tk.StringVar()

        if self.paths:
            self.save_var.set(self.paths[0])
            self.photos_var.set(self.paths[1])
            self.videos_var.set(self.paths[2])
        else:
            try:
                self._restore_defaults()
            except Exception as e:
                print("Erreur lors du chargement des chemins par défaut :", e)

        self.restore_button = ctk.CTkButton(
            frame,
            text="Rétablir valeurs par défaut",
            command=self._restore_defaults,
            fg_color="grey",
            width=220
        )
        self.restore_button.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        labels = [
            ("Emplacement de sauvegarde :", self.save_var),
            ("Emplacement photos existantes :", self.photos_var),
            ("Emplacement vidéos existantes :", self.videos_var)
        ]
        for i, (text, var) in enumerate(labels, start=1):
            ctk.CTkLabel(frame, text=text).grid(row=i, column=0, sticky="w", pady=5)
            entry = ctk.CTkEntry(frame, textvariable=var)
            entry.grid(row=i, column=1, padx=5, pady=5, sticky="ew")  # s'étire horizontalement
            ctk.CTkButton(
                frame,
                text="Parcourir",
                width=100,
                command=lambda v=var: self._browse(v)
            ).grid(row=i, column=2, padx=5, pady=5, sticky="e")

        self.launch_button = ctk.CTkButton(
            self,
            text="Lancer le téléchargement (ADB)",
            command=self._launch,
            state="disabled",
            width=250
        )
        self.launch_button.pack(pady=20)

        for var in (self.save_var, self.photos_var, self.videos_var):
            var.trace_add("write", lambda *_: self._update_launch_button())
        self._update_launch_button()


    def _browse(self, var):
        path = filedialog.askdirectory()
        if path:
            var.set(path.replace("/", "\\"))

    def _restore_defaults(self):
        save, photos, videos = get_default_paths()
        self.save_var.set(save)
        self.photos_var.set(photos)
        self.videos_var.set(videos)

    def _update_launch_button(self):
        filled = all(v.get().strip() for v in
                     (self.save_var, self.photos_var, self.videos_var))
        state = "normal" if filled else "disabled"
        self.launch_button.configure(state=state)

    def _launch(self):
        data = {
            "save":   self.save_var.get(),
            "photos": self.photos_var.get(),
            "videos": self.videos_var.get()
        }
        # Sauvegarde de la configuration dans config.json
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        # Libérer le grab modal AVANT fermeture
        self.grab_release()

        # Supprimer tout bind éventuel qui redonne le focus
        self.unbind("<FocusIn>")

        # Fermer la SettingsADBWindow
        self.master.secondary_window = None
        self.destroy()

        # Ouvrir la fenêtre ADB juste après destruction
        self.master.open_modal(ADBWindow,
                               download_photos=self.download_photos,
                               download_videos=self.download_videos)     

class ADBWindow(ModalWindow):
    def __init__(self, master, download_photos=True, download_videos=True):
        super().__init__(master, title="Téléchargement ADB", size="900x500", icon_path="icon.ico")
        
        self.download_photos = download_photos
        self.download_videos = download_videos
        
        self.cancel_flag = CancelFlag()

        self._load_config()
        self._create_widgets()

        self.spinner = SpinnerWidget(self)
        self.spinner.start()  

        threading.Thread(target=self._start_download, daemon=True).start()
    
    def _load_config(self):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.save_path   = data.get("save", "")
        self.photos_path = data.get("photos", "")
        self.videos_path = data.get("videos", "")

    def _create_widgets(self):
        self.progress_label = ctk.CTkLabel(self, text="Progression : 0 / 0")
        self.progress_label.pack(pady=(20, 5))

        self.progressbar = ctk.CTkProgressBar(self, width=700)
        self.progressbar.set(0)
        self.progressbar.pack(pady=10)

        self.console = scrolledtext.ScrolledText(
            self,
            height=18,
            state="disabled",
            font=("IBM Plex Mono", 10),
            wrap="none"
        )
        self.console.pack(pady=10, fill="both", expand=True)

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=10)

        self.cancel_button = ctk.CTkButton(
            btn_frame, text="Annuler", command=self._request_cancel, fg_color="red"
        )
        self.cancel_button.grid(row=0, column=0, padx=10)

        self.finish_button = ctk.CTkButton(
            btn_frame, text="Terminer", command=self._on_close, state="disabled"
        )
        self.finish_button.grid(row=0, column=1, padx=10)

    def _request_cancel(self):
        self.cancel_flag.cancelled = True
        self._log("Annulation demandée...")
    
    def _log(self, message):
        self.console.configure(state="normal")
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)
        self.console.configure(state="disabled")

    def _update_progress(self, done, total):
        if total == 0:
            self.progressbar.set(0)
            self.progress_label.configure(text="Progression : 0 / 0")
        else:
            ratio = done / total
            self.progressbar.set(ratio)
            self.progress_label.configure(text=f"Progression : {done} / {total}")

    def _on_close(self):
        self._request_cancel()
        super()._on_close()

    def _start_download(self):
        run_adb_download(
            self.save_path,
            self.photos_path,
            self.videos_path,
            log_callback=lambda msg: self.after(0, self._log, msg),
            progress_callback=lambda d, t: self.after(0, self._update_progress, d, t),
            cancel_flag=self.cancel_flag,
            download_photos=self.download_photos,
            download_videos=self.download_videos
        )

        self.spinner.stop("✅")
        self.after(0, lambda: self.progress_label.configure(text="✅ Téléchargement terminé"))
        self.after(0, lambda: self.finish_button.configure(state="normal"))
        self.after(0, lambda: self.cancel_button.configure(state="disabled"))

class SettingsSortWindow(ModalWindow):
    def __init__(self, master):
        super().__init__(master, title="Paramètres de tri", size="750x400", icon_path="icon.ico")
        
        config_path = resource_path("assets/config.json")

        with open(config_path, "r", encoding="utf-8") as f:
            self.config_data = json.load(f)

        self.var_save   = ctk.StringVar(value=self.config_data.get("save", ""))
        self.var_photos = ctk.StringVar(value=self.config_data.get("photos", ""))
        self.var_videos = ctk.StringVar(value=self.config_data.get("videos", ""))

        self._create_widgets()
        self._update_save_button_state()

        for var in (self.var_save, self.var_photos, self.var_videos):
            var.trace_add("write", lambda *args: self._update_save_button_state())
    
    def _create_widgets(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        frame.grid_columnconfigure(1, weight=1)

        # Champ téléchargement
        ctk.CTkLabel(frame, text="Emplacement des médias à renommer et trier :").grid(row=0, column=0, sticky="w", pady=5)
        entry_save = ctk.CTkEntry(frame, textvariable=self.var_save, width=400)
        entry_save.grid(row=0, column=1, sticky="ew", padx=5)
        ctk.CTkButton(frame, text="Parcourir", command=self._browse_save).grid(row=0, column=2, padx=5)

        # Champ photos
        ctk.CTkLabel(frame, text="Emplacement de destination pour les photos :").grid(row=1, column=0, sticky="w", pady=5)
        entry_photos = ctk.CTkEntry(frame, textvariable=self.var_photos, width=400)
        entry_photos.grid(row=1, column=1, sticky="ew", padx=5)
        ctk.CTkButton(frame, text="Parcourir", command=self._browse_photos).grid(row=1, column=2, padx=5)

        # Champ vidéos
        ctk.CTkLabel(frame, text="Emplacement de destination pour les vidéos :").grid(row=2, column=0, sticky="w", pady=5)
        entry_videos = ctk.CTkEntry(frame, textvariable=self.var_videos, width=400)
        entry_videos.grid(row=2, column=1, sticky="ew", padx=5)
        ctk.CTkButton(frame, text="Parcourir", command=self._browse_videos).grid(row=2, column=2, padx=5)

        # Bouton enregistrer
        self.btn_save = ctk.CTkButton(self, text="Enregistrer", command=self._save_config)
        self.btn_save.pack(pady=(0, 20))

    def _browse_save(self):
        path = ctk.filedialog.askdirectory(title="Sélectionner dossier de tri")
        if path:
            self.var_save.set(path.replace("/", "\\"))

    def _browse_photos(self):
        path = ctk.filedialog.askdirectory(title="Sélectionner dossier Photos")
        if path:
            self.var_photos.set(path.replace("/", "\\"))

    def _browse_videos(self):
        path = ctk.filedialog.askdirectory(title="Sélectionner dossier Vidéos")
        if path:
            self.var_videos.set(path.replace("/", "\\"))

    def _update_save_button_state(self):
        ok = all(v.get().strip() for v in (self.var_save, self.var_photos, self.var_videos))
        self.btn_save.configure(state="normal" if ok else "disabled")

    def _save_config(self):
        self.config_data["save"]   = self.var_save.get().strip()
        self.config_data["photos"] = self.var_photos.get().strip()
        self.config_data["videos"] = self.var_videos.get().strip()
        with open(resource_path("assets/config.json"), "w", encoding="utf-8") as f:
            json.dump(self.config_data, f, indent=4, ensure_ascii=False)
        
        self.grab_release()
        self.master.secondary_window = None
        self.destroy()

        self.master.open_modal(SortWindow)

class SortWindow(ModalWindow):
    def __init__(self, master):
        super().__init__(master, title="Tri et sauvegarde", size="900x500", icon_path="icon.ico")
        
        self.cancel_flag = CancelFlag()

        self._load_config()
        self._create_widgets()

        self.spinner = SpinnerWidget(self)
        self.spinner.start()

        # Lancer le tri dans un thread séparé
        threading.Thread(target=self._start_sort, daemon=True).start()
    
    def _load_config(self):
        with open(resource_path("assets/config.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
        self.save_path   = data.get("save", "")
        self.photos_path = data.get("photos", "")
        self.videos_path = data.get("videos", "")

    def _create_widgets(self):
        self.progress_label = ctk.CTkLabel(self, text="Progression : 0 / 0")
        self.progress_label.pack(pady=(20, 5))

        self.progressbar = ctk.CTkProgressBar(self, width=700)
        self.progressbar.set(0)
        self.progressbar.pack(pady=10)

        self.console = scrolledtext.ScrolledText(
            self,
            height=18,
            state="disabled",
            font=("IBM Plex Mono", 10),
            wrap="none"
        )
        self.console.pack(pady=10, fill="both", expand=True)

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=10)

        self.cancel_button = ctk.CTkButton(
            btn_frame, text="Annuler", command=self._request_cancel, fg_color="red"
        )
        self.cancel_button.grid(row=0, column=0, padx=10)

        self.finish_button = ctk.CTkButton(
            btn_frame, text="Terminer", command=self._on_close, state="disabled"
        )
        self.finish_button.grid(row=0, column=1, padx=10)

    def _log(self, message):
        self.console.configure(state="normal")
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)
        self.console.configure(state="disabled")

    def _update_progress(self, done, total):
        if total == 0:
            self.progressbar.set(0)
            self.progress_label.configure(text="Progression : 0 / 0")
        else:
            ratio = done / total
            self.progressbar.set(ratio)
            self.progress_label.configure(text=f"Progression : {done} / {total}")

    def _request_cancel(self):
        self.cancel_flag.cancelled = True
        self._log("Annulation demandée...")

    def _on_close(self):
        self._request_cancel()
        self.grab_release()
        self.master.secondary_window = None
        self.destroy()

    def _start_sort(self):
        sort_and_save_files(
            self.save_path,
            self.photos_path,
            self.videos_path,
            log_callback=lambda msg: self.after(0, self._log, msg),
            progress_callback=lambda d, t: self.after(0, self._update_progress, d, t),
            cancel_flag=self.cancel_flag
        )

        self.spinner.stop("✅")
        self.after(0, lambda: self.progress_label.configure(text="Tri terminé"))
        self.after(0, lambda: self.finish_button.configure(state="normal"))
        self.after(0, lambda: self.cancel_button.configure(state="disabled"))

class SettingsBackupWindow(ModalWindow):
    def __init__(self, master):
        super().__init__(master, title="Paramètres du backup HDD", size="750x400", icon_path="icon.ico")

        with open(resource_path("assets/config.json"), "r", encoding="utf-8") as f:
            self.config_data = json.load(f)

        self.var_photos = ctk.StringVar(value=self.config_data.get("photos", ""))
        self.var_videos = ctk.StringVar(value=self.config_data.get("videos", ""))
        self.var_backup = ctk.StringVar(value=self.config_data.get("backup", ""))

        self._create_widgets()
        self._update_save_button_state()
    
    def _create_widgets(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        frame.grid_columnconfigure(1, weight=1)  # colonne des Entry extensible

        # Photos
        ctk.CTkLabel(frame, text="Emplacement des photos existantes :").grid(row=0, column=0, sticky="w", pady=5)
        entry_ph = ctk.CTkEntry(frame, textvariable=self.var_photos, width=400)
        entry_ph.grid(row=0, column=1, sticky="ew", padx=5)
        ctk.CTkButton(frame, text="Parcourir", command=self._browse_photos).grid(row=0, column=2, padx=5)

        # Vidéos
        ctk.CTkLabel(frame, text="Emplacement des vidéos existantes :").grid(row=1, column=0, sticky="w", pady=5)
        entry_vid = ctk.CTkEntry(frame, textvariable=self.var_videos, width=400)
        entry_vid.grid(row=1, column=1, sticky="ew", padx=5)
        ctk.CTkButton(frame, text="Parcourir", command=self._browse_videos).grid(row=1, column=2, padx=5)

        # Backup
        ctk.CTkLabel(frame, text="Dossier de backup externe :").grid(row=2, column=0, sticky="w", pady=5)

        # Bordure rouge si vide
        backup_path = self.var_backup.get().strip()
        if backup_path:
            self.entry_bu = ctk.CTkEntry(
                frame,
                textvariable=self.var_backup,
                width=400
            )
        else:
            self.entry_bu = ctk.CTkEntry(
                frame,
                textvariable=self.var_backup,
                width=400,
                border_color="red"
            )

        self.entry_bu.grid(row=2, column=1, sticky="ew", padx=5)
        ctk.CTkButton(frame, text="Parcourir", command=self._browse_backup).grid(row=2, column=2, padx=5)

        # Bouton enregistrer
        self.btn_save = ctk.CTkButton(self, text="Enregistrer", command=self._save_config)
        self.btn_save.pack(pady=(0, 20))


        # Suivi des modifications
        for var in (self.var_photos, self.var_videos, self.var_backup):
            var.trace_add("write", lambda *args: self._update_save_button_state())

    def _browse_photos(self):
        path = ctk.filedialog.askdirectory(title="Sélectionner dossier Photos")
        if path:
            path = path.replace("/", "\\")

            self.var_photos.set(path)

    def _browse_videos(self):
        path = ctk.filedialog.askdirectory(title="Sélectionner dossier Vidéos")
        if path:
            path = path.replace("/", "\\")

            self.var_videos.set(path)

    def _browse_backup(self):
        path = ctk.filedialog.askdirectory(title="Sélectionner dossier Backup")
        if path:
            path = path.replace("/", "\\")

            self.var_backup.set(path)
            self.entry_bu.configure(border_color="green")

    def _update_save_button_state(self):
        # Active si tous les champs sont non vides
        ok = all(v.get().strip() for v in (self.var_photos, self.var_videos, self.var_backup))
        self.btn_save.configure(state="normal" if ok else "disabled")

    def _save_config(self):
        self.config_data["photos"] = self.var_photos.get().strip()
        self.config_data["videos"] = self.var_videos.get().strip()
        self.config_data["backup"] = self.var_backup.get().strip()

        with open(resource_path("assets/config.json"), "w", encoding="utf-8") as f:
            json.dump(self.config_data, f, indent=4, ensure_ascii=False)

        self.grab_release()
        self.unbind("<FocusIn>")
        self.master.secondary_window = None
        self.destroy()
        self.master.open_modal(BackupWindow)

class BackupWindow(ModalWindow):
    def __init__(self, master):
        super().__init__(master, title="Exécution du backup", size="900x500", icon_path="icon.ico")

        self.cancel_flag = CancelFlag()

        # Charger config
        with open(resource_path("assets/config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.photo_src = cfg["photos"]
        self.video_src = cfg["videos"]
        self.backup_dest = cfg["backup"]

        # Calcul du total de fichiers AVANT affichage
        def count_files(path):
            total = 0
            for _, _, files in os.walk(path):
                total += len(files)
            return total
        self.total_files = count_files(self.photo_src) + count_files(self.video_src)

        # Widgets
        self.progress_label = ctk.CTkLabel(self, text=f"Progression : 0 / {self.total_files}")
        self.progress_label.pack(pady=(20, 5))

        self.progressbar = ctk.CTkProgressBar(self, width=700)
        self.progressbar.set(0)
        self.progressbar.pack(pady=10)

        self.spinner = SpinnerWidget(self)
        self.spinner.spinner_label.pack(pady=(0, 10))
        self.spinner.start()

        # Console adaptative + alignement gauche
        self.console = scrolledtext.ScrolledText(
            self,
            height=18,
            state="disabled",
            font=("IBM Plex Mono", 10),
            wrap="none"
        )
        self.console.tag_configure("left", justify="left")
        self.console.pack(pady=10, fill="both", expand=True)

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=10)

        self.cancel_button = ctk.CTkButton(
            btn_frame, text="Annuler", command=self._request_cancel, fg_color="red"
        )
        self.cancel_button.grid(row=0, column=0, padx=10)

        self.finish_button = ctk.CTkButton(
            btn_frame, text="Terminer", command=self._on_close, state="disabled"
        )
        self.finish_button.grid(row=0, column=1, padx=10)

        # Lancer le backup dans un thread séparé
        threading.Thread(target=self._run_backup, daemon=True).start()

    def _log(self, msg):
        self.console.configure(state="normal")
        self.console.insert(tk.END, msg + "\n", "left")
        self.console.see(tk.END)
        self.console.configure(state="disabled")

    def _update_progress(self, done, total):
        ratio = done / total if total else 0
        self.progressbar.set(ratio)
        self.progress_label.configure(text=f"Progression : {done} / {total}")

    def _request_cancel(self):
        self.cancel_flag.cancelled = True
        self._log("Annulation demandée…")

    def _on_close(self):
        """Fermeture propre, que ce soit via le bouton ou la croix."""
        self._request_cancel()
        super()._on_close()

    def _run_backup(self):
        success, _ = run_backup(
            self.photo_src,
            self.video_src,
            self.backup_dest,
            log_callback=lambda m: self.after(0, self._log, m),
            progress_callback=lambda d, t: self.after(0, self._update_progress, d, t),
            cancel_flag=self.cancel_flag
        )

        self.spinner.stop("✅" if success else "⚠")
        self.after(0, lambda: self.progress_label.configure(
            text="✅ Backup terminé" if success else "⚠ Backup interrompu"
        ))
        self.after(0, lambda: self.finish_button.configure(state="normal"))
        self.after(0, lambda: self.cancel_button.configure(state="disabled"))

class ChangelogWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Changelog")
        self.geometry("500x400")      
        self.resizable(False, False)
        self.transient(master)
        self.focus_set()
        self.lift()
        ico_path = os.path.abspath(resource_path("icon.ico"))
        self.iconbitmap(ico_path)

        # Choix de la police
        changelog_font = ctk.CTkFont(family="IBM Plex Mono", size=12)

        # Scrolling
        self.textbox = ctk.CTkTextbox(self, font=changelog_font, wrap="word", activate_scrollbars=True)
        self.textbox.pack(expand=True, fill="both", padx=20, pady=20)

        # Chargement de Changelog.txt
        try:
            with open(resource_path("assets/changelog.txt"), "r", encoding="utf-8") as f:
                content = f.read()
                self.textbox.insert("0.0", content)
        except Exception as e:
            self.textbox.insert("0.0", f"Erreur lors du chargement du changelog : \n{e}")

        self.textbox.configure(state="disabled") # Lecture seule

if __name__ == "__main__":

    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = MainApp()
    app.mainloop()