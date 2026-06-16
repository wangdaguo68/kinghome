#!/usr/bin/env bash
set -euo pipefail

mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/node" <<'EOF'
#!/usr/bin/env bash
exec node.exe "$@"
EOF
chmod +x "$HOME/.local/bin/node"

export PATH="$HOME/.local/bin:$PATH"
command -v node
node --version
command -v codex
codex --version
