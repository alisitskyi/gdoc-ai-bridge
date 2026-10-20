#!/usr/bin/env bash
# macOS / Linux Installer for gdoc-ai-bridge
set -e

echo "=========================================="
echo "  Installing gdoc-ai-bridge (Unix)        "
echo "=========================================="

# 1. Check Python
PYTHON_CMD=$(which python3 || which python || true)
if [ -z "$PYTHON_CMD" ]; then
    echo "[ERROR] Python 3 is not installed or not in PATH."
    exit 1
fi
echo "[+] Found Python: $PYTHON_CMD"

# 2. Install dependencies
echo "[*] Installing Python dependencies..."
$PYTHON_CMD -m pip install -r "$(dirname "$0")/requirements.txt" --quiet
echo "[+] Dependencies installed successfully."

# 3. Create ~/.gdoc directory
GDOC_HOME="$HOME/.gdoc"
GDOC_BIN="$GDOC_HOME/bin"
mkdir -p "$GDOC_BIN"

cp "$(dirname "$0")/src/gdoc_ai/cli.py" "$GDOC_HOME/gdoc_tool.py"

# Create unix wrappers
cat << 'EOF' > "$GDOC_BIN/gdoc"
#!/usr/bin/env bash
python3 "$HOME/.gdoc/gdoc_tool.py" "$@"
EOF
chmod +x "$GDOC_BIN/gdoc"

cat << 'EOF' > "$GDOC_BIN/gsheet"
#!/usr/bin/env bash
python3 "$HOME/.gdoc/gdoc_tool.py" "$@"
EOF
chmod +x "$GDOC_BIN/gsheet"

# 4. PATH hint
SHELL_RC=""
if [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
fi

if [ -n "$SHELL_RC" ]; then
    if ! grep -q "$GDOC_BIN" "$SHELL_RC"; then
        echo "export PATH=\"\$PATH:$GDOC_BIN\"" >> "$SHELL_RC"
        echo "[+] Added $GDOC_BIN to $SHELL_RC"
    fi
fi

echo ""
echo "[+] Installation complete!"
echo "1. Place your Google Cloud OAuth JSON as: $GDOC_HOME/credentials.json"
echo "2. Run: gdoc auth"
