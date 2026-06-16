#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  Evony Bot — One-click setup for Linux / macOS
#  Downloads and configures every requirement, then you're done.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

echo
echo "============================================================"
echo "   Evony Bot - Automated Setup"
echo "============================================================"
echo

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "[X] Python was not found. Install Python 3.10+ and re-run ./setup.sh"
    exit 1
fi

echo "Using: $($PY --version)"
echo

cd "$(dirname "$0")"
"$PY" deploy.py "$@"
RC=$?

echo
if [ "$RC" -eq 0 ]; then
    echo "Setup complete. Launch the bot with:  $PY gui.py"
else
    echo "Setup reported problems (exit $RC). See the messages above."
fi
exit $RC
