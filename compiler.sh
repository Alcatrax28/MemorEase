#!/bin/bash
# ============================================================
#  Compilateur MemorEase — Linux
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Compilation ---
cd "$SCRIPT_DIR"

if [ -f "$SCRIPT_DIR/.venv/bin/pyinstaller" ]; then
    PYINSTALLER="$SCRIPT_DIR/.venv/bin/pyinstaller"
else
    PYINSTALLER="pyinstaller"
fi

"$PYINSTALLER" MemorEase.spec

echo ""
echo "[DONE] Exécutable généré dans : $SCRIPT_DIR/dist/"
