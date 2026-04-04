#!/bin/bash
# ============================================================
#  Compilateur MemorEase — Linux
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADB_DEST="$SCRIPT_DIR/assets/adb/adb"
ADB_URL="https://dl.google.com/android/repository/platform-tools-latest-linux.zip"
TMP_ZIP="/tmp/platform-tools-linux.zip"

# --- Téléchargement du binaire ADB Linux si absent ---
if [ ! -f "$ADB_DEST" ]; then
    echo "[INFO] Binaire ADB Linux introuvable, téléchargement..."
    curl -L "$ADB_URL" -o "$TMP_ZIP"
    unzip -j "$TMP_ZIP" "platform-tools/adb" -d "$(dirname "$ADB_DEST")"
    chmod +x "$ADB_DEST"
    rm -f "$TMP_ZIP"
    echo "[OK] ADB Linux prêt : $ADB_DEST"
else
    echo "[OK] ADB Linux déjà présent : $ADB_DEST"
fi

# --- Compilation ---
cd "$SCRIPT_DIR"
pyinstaller MemorEase.spec

echo ""
echo "[DONE] Exécutable généré dans : $SCRIPT_DIR/dist/"
