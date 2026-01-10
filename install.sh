#!/data/data/com.termux/files/usr/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[1/3] Install Python dependencies"
pip install -r "$ROOT_DIR/requirements.txt"

echo "[2/3] Create alias 'dor'"
PROFILE="$HOME/.bashrc"
if [ -n "$SHELL" ] && [ -f "$HOME/.zshrc" ]; then
  PROFILE="$HOME/.zshrc"
fi
ALIAS_LINE="alias dor='python $ROOT_DIR/main.py'"
if ! grep -Fq "$ALIAS_LINE" "$PROFILE" 2>/dev/null; then
  echo "$ALIAS_LINE" >> "$PROFILE"
fi

echo "[3/3] Done. Restart Termux or run: source $PROFILE"
echo "Then type: dor"
