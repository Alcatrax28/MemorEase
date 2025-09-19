# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # --- assets/adb ---
        ('assets/adb/adb.exe', 'assets/adb'),
        ('assets/adb/AdbWinApi.dll', 'assets/adb'),
        ('assets/adb/AdbWinUsbApi.dll', 'assets/adb'),

        # --- assets/fonts ---
        ('assets/fonts/IBM-Logo.ttf', 'assets/fonts'),
        ('assets/fonts/IBMPlexMono-Regular.ttf', 'assets/fonts'),

        # --- fichiers racine de assets ---
        ('assets/changelog.txt', 'assets'),
        ('assets/config.json', 'assets'),
        ('assets/version.txt', 'assets'),

        # --- icône ---
        ('icon.ico', '.'),
    ],
    hiddenimports=[
        'sort_tools',  
        'adb_tools',   
        'backup',      
        'spinner_widget',
        'requests',
        'CTkMessagebox',
        'update_maker',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MemorEase',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                   # pas de console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',                  # icône intégrée à l'exe
)