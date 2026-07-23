#!/usr/bin/env bash
# project-setup.sh — install the nb2lite-image skill into a target project and
# register the NB2Lite MCP server in its .mcp.json. Idempotent; safe to re-run.
#
# Usage:
#   mcp/project-setup.sh /path/to/project [options]   # one project
#   mcp/project-setup.sh --global [options]           # all projects (user scope)
#
# Options:
#   --model <name>        GEMINI_MODEL_NAME for the server (default: gemini-3.1-flash-lite-image)
#   --output-dir <dir>    IMAGE_OUTPUT_DIR for saved images (default: server default, ".")
#   --server-name <name>  MCP server key in .mcp.json (default: nb2lite-agent)
#   --skip-deps           Skip the pip dependency check
#   -h | --help           Show this help
#
# The Gemini API key is read from ~/gemini.key when present and injected into the
# server's env block. Otherwise the entry is written without a key and you must
# run set_env.sh (or export GEMINI_API_KEY) before the server will work.
set -euo pipefail

SKILL_NAME="nb2lite-image"
SERVER_NAME="nb2lite-agent"
MODEL_NAME="gemini-3.1-flash-lite-image"
OUTPUT_DIR=""
SKIP_DEPS=0
GLOBAL=0
TARGET=""

usage() { sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
    case "$1" in
        --global) GLOBAL=1 ;;
        --model) MODEL_NAME="$2"; shift ;;
        --output-dir) OUTPUT_DIR="$2"; shift ;;
        --server-name) SERVER_NAME="$2"; shift ;;
        --skip-deps) SKIP_DEPS=1 ;;
        -h|--help) usage; exit 0 ;;
        -*) echo "Unknown option: $1" >&2; usage; exit 1 ;;
        *)
            if [ -n "$TARGET" ]; then
                echo "Only one target directory may be given." >&2; exit 1
            fi
            TARGET="$1"
            ;;
    esac
    shift
done

if [ "$GLOBAL" -eq 0 ] && [ -z "$TARGET" ]; then
    usage; exit 1
fi
if [ "$GLOBAL" -eq 1 ] && [ -n "$TARGET" ]; then
    echo "--global and a target directory are mutually exclusive." >&2; exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_SRC="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Copy the skill into place ------------------------------------------------
if [ "$GLOBAL" -eq 1 ]; then
    DEST="$HOME/.gemini/antigravity-cli/skills/$SKILL_NAME"
else
    TARGET="$(cd "$TARGET" && pwd)"
    DEST="$TARGET/.gemini/antigravity-cli/skills/$SKILL_NAME"
fi

mkdir -p "$DEST/mcp" "$DEST/references"
cp "$SKILL_SRC/SKILL.md" "$DEST/SKILL.md"
cp "$SKILL_SRC/mcp/server.py" "$DEST/mcp/server.py"
cp "$SKILL_SRC/mcp/requirements.txt" "$DEST/mcp/requirements.txt"
cp "$SKILL_SRC/mcp/project-setup.sh" "$DEST/mcp/project-setup.sh"
chmod +x "$DEST/mcp/project-setup.sh" 2>/dev/null || true
cp "$SKILL_SRC"/references/*.md "$DEST/references/"
echo "✅ Installed skill to $DEST"

# --- Dependency check (warn only; never creates a venv) -----------------------
if [ "$SKIP_DEPS" -eq 0 ]; then
    if ! python3 -c "import google.genai, mcp" >/dev/null 2>&1; then
        echo "⚠️  Missing Python deps for the system python3. Install with:"
        echo "    pip install -r $DEST/mcp/requirements.txt"
    fi
fi

# --- Gemini API key -----------------------------------------------------------
API_KEY=""
if [ -f "$HOME/gemini.key" ]; then
    API_KEY="$(cat "$HOME/gemini.key")"
    echo "✅ Using Gemini API key from ~/gemini.key"
else
    echo "⚠️  No ~/gemini.key found. Run set_env.sh (or export GEMINI_API_KEY)"
    echo "    before starting the server — it will refuse requests without a key."
fi

# --- Register the MCP server --------------------------------------------------
if [ "$GLOBAL" -eq 1 ]; then
    echo "✅ Skill installed globally to $DEST"
    echo "ℹ️  Ensure your .mcp.json or server configuration points to $DEST/mcp/server.py"
else
    CONFIG_FILE="$TARGET/.mcp.json" DEST="$DEST" SERVER_NAME="$SERVER_NAME" \
    MODEL_NAME="$MODEL_NAME" OUTPUT_DIR="$OUTPUT_DIR" API_KEY="$API_KEY" python3 - <<'EOF'
import json, os

config_file = os.environ["CONFIG_FILE"]
data = {}
if os.path.exists(config_file):
    with open(config_file) as f:
        data = json.load(f)
servers = data.setdefault("mcpServers", {})

env = {"GEMINI_MODEL_NAME": os.environ["MODEL_NAME"]}
if os.environ.get("API_KEY"):
    env["GEMINI_API_KEY"] = os.environ["API_KEY"]
    env["GOOGLE_API_KEY"] = os.environ["API_KEY"]
if os.environ.get("OUTPUT_DIR"):
    env["IMAGE_OUTPUT_DIR"] = os.environ["OUTPUT_DIR"]

servers[os.environ["SERVER_NAME"]] = {
    "command": "python3",
    "args": [os.environ["DEST"] + "/mcp/server.py"],
    "env": env,
}
with open(config_file, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
print(f"✅ Registered '{os.environ['SERVER_NAME']}' in {config_file}")
EOF
    if [ -n "$API_KEY" ]; then
        echo "ℹ️  .mcp.json now contains your API key — keep it gitignored."
    fi
fi

echo ""
echo "Done. Restart Antigravity CLI in the target project;"
echo "the MCP server '$SERVER_NAME' will be active."
