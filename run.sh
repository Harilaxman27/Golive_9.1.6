#!/usr/bin/env bash
set -euo pipefail

# Run GoLive Studio using the project's virtual environment.
# This script handles paths with spaces and prints diagnostic info before launching.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VEVN_ACTIVATE="$DIR/venv/bin/activate"
if [ ! -f "$VEVN_ACTIVATE" ]; then
  echo "Virtualenv activate not found at: $VEVN_ACTIVATE"
  echo "Create the venv first with: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

# Source the venv (quotes handle spaces)
# shellcheck disable=SC1090
. "$VEVN_ACTIVATE"

echo "Using python: $(which python)"
python -V

echo "Checking PyQt6 availability..."
python - <<'PY'
try:
    import PyQt6
    from PyQt6 import QtCore
    print('PyQt6 present, PyQt version:', getattr(QtCore, 'PYQT_VERSION_STR', 'unknown'))
    print('Qt version:', getattr(QtCore, 'QT_VERSION_STR', 'unknown'))
except Exception as e:
    print('PyQt6 import failed:', e)
    raise
PY

echo "Launching GoLive Studio..."
exec python "$DIR/main.py"
