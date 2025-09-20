import os
import json
import getpass
import string
from utils import resource_path # pyright: ignore[reportMissingImports]

def find_onedrive():
    for drive in (f"{d}:\\" for d in string.ascii_uppercase):
        users_dir = os.path.join(drive, "Users")
        if not os.path.isdir(users_dir):
            continue
        for user_folder in os.listdir(users_dir):
            base = os.path.join(users_dir, user_folder)
            if not os.path.isdir(base):
                continue
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

def load_paths():
    config_path = resource_path("assets/config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            save, photos, videos = (
                data.get("save"),
                data.get("photos"),
                data.get("videos"),
            )
            if all(isinstance(p, str) and p for p in (save, photos, videos)):
                return save, photos, videos
    except Exception:
        pass
    return get_default_paths()

def save_paths(save, photos, videos):
    config_path = resource_path("assets/config.json")
    data = {
        "save": save,
        "photos": photos,
        "videos": videos
    }
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass