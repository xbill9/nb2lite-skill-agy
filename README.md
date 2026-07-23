# 🌌 NB2Lite Agent

[![Model: gemini-3.1-flash-lite-image](https://img.shields.io/badge/Model-gemini--3.1--flash--lite--image-orange.svg)](#)
[![API: Interactions API](https://img.shields.io/badge/API-Interactions%20API-blue.svg)](GEMINI.md)
[![Protocol: FastMCP](https://img.shields.io/badge/Protocol-FastMCP-green.svg)](#)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-lightgrey.svg)](LICENSE)

This repository contains a high-performance Model Context Protocol (MCP) server for interacting with **gemini-3.1-flash-lite-image**, Google's high-efficiency Gemini Image model designed for exceptional speed, low latency, and high-fidelity image generation and editing.

Unlike traditional stateless image models, `gemini-3.1-flash-lite-image` supports the stateful **Interactions API**, allowing AI agents and developers to iteratively edit, refine, and transform images using natural language within a single context session.

---

## ✨ Features

- ⚡ **Low Latency & High Scale**: Under 2-second generation times, offering exceptional quality with blazing-fast speeds.
- 🔄 **Stateful Multi-Turn Edits**: Maintain pixel and contextual continuity across multiple edits using interaction IDs.
- 🎨 **Inline Local Image Modding**: Upload existing images in-line via Base64 and describe your edits directly.
- 🧠 **Thinking Budgets**: Adjust latency vs. quality with configurable reasoning steps (`low`, `high`).
- ✍️ **Enhanced Text & i18n**: Advanced text rendering in English and 25+ other languages.
- 📂 **Concurrent File Management**: Thread-safe image saving with UUID-appended unique file naming and custom output folders.

---

## ⚙️ Environment Configuration

The MCP server checks the following environment variables on startup and execution:

| Variable | Type | Description | Default |
| :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | `str` | Primary API Key used to authenticate with the Gemini API. | *Required (or fallback)* |
| `GOOGLE_API_KEY` | `str` | Fallback API Key used if `GEMINI_API_KEY` is not defined. | *Optional* |
| `GEMINI_MODEL_NAME` | `str` | Overrides the default model used for interactions. | `"gemini-3.1-flash-lite-image"` |
| `IMAGE_OUTPUT_DIR` | `str` | Sets the local directory where generated/edited images are stored. | `"."` (current directory) |

---

## 🚀 Getting Started

### 1. Prerequisites

Ensure you have Python 3.10+ installed, then clone the repo and install the required dependencies using the [Makefile](Makefile) or pip:

```bash
git clone https://github.com/xbill9/nb2lite-skill-claude.git
cd nb2lite-skill-claude
make install
# or
pip install -r requirements.txt
```

### 2. Configure Environment

You can configure your credentials interactively or reuse an existing key file using the helper script:

```bash
# Set up environment and export credentials
source set_env.sh
```

> [!NOTE]
> The `set_env.sh` script automatically reads your key from `~/gemini.key` if it exists. If not, it prompts you for the key, stores it securely in `~/gemini.key` for persistence across sessions, and exports both `GEMINI_API_KEY` and `GOOGLE_API_KEY` (fallback).

### 3. One-Command Bootstrap (Claude Code)

To use the agent from Claude Code in this repo, `./init.sh` does the full local setup in one pass — installs the Python dependencies, registers the `nb2lite-agent` MCP server in this repo's `.mcp.json` (pointing at the repo-root [server.py](server.py)), and runs `set_env.sh` for the API key:

```bash
./init.sh        # or: source init.sh   (also exports the key into your shell)
```

Then restart Claude Code in the repo and approve the server; `/mcp` should list `nb2lite-agent`.

---

## 🤖 MCP Server Integration

The FastMCP server defined in [server.py](server.py) exposes the full capabilities of `gemini-3.1-flash-lite-image` directly to your AI agents or assistants as tools.

### Run the Server

You can run the server locally or in development mode using:

```bash
make run
# or run with MCP dev tools
mcp dev server.py
```

### 🛠️ Exposed Tools

#### 1. `generate_image`
Generates a 1k resolution image from a text prompt and saves it locally.

* **Arguments**:
  - `prompt` (`str`): The natural language description of the image.
  - `aspect_ratio` (`str`): Supported: `1:1`, `16:9`, `9:16`, `4:3`, `3:4` (Default: `"1:1"`).
  - `thinking_level` (`str`): Configurable thinking budget: `low`, `high` (Default: `"low"`).
* **Usage Example**:
  ```python
  # Tool Call
  generate_image(prompt="A futuristic cyberpunk kitchen cooking noodles", aspect_ratio="16:9", thinking_level="high")
  ```

#### 2. `edit_image`
Iteratively refines or modifies an existing image while preserving pixel and contextual continuity.

* **Arguments**:
  - `previous_interaction_id` (`str`): The unique ID returned from the previous generation or edit.
  - `edit_prompt` (`str`): Natural language description of what to change or add in the image.
  - `thinking_level` (`str`): Configurable thinking budget: `low`, `high` (Default: `"low"`).
* **Usage Example**:
  ```python
  # Tool Call
  edit_image(previous_interaction_id="int_abc123xyz", edit_prompt="add a neon green glowing sign saying 'RAMEN' on the wall", thinking_level="high")
  ```

#### 3. `edit_local_image`
Uploads a local image file in-line via Base64 and applies edits described in natural language.

* **Arguments**:
  - `image_path` (`str`): Absolute or relative path to the local image file.
  - `edit_prompt` (`str`): Natural language description of how to edit or modify the image.
  - `aspect_ratio` (`str`): Supported: `1:1`, `16:9`, `9:16`, `4:3`, `3:4` (Default: `"1:1"`).
  - `thinking_level` (`str`): Configurable thinking budget: `low`, `high` (Default: `"low"`).
* **Usage Example**:
  ```python
  # Tool Call
  edit_local_image(image_path="./my_sketch.png", edit_prompt="Render this hand-drawn sketch as a high-fidelity 3D model", aspect_ratio="4:3")
  ```

#### 4. `get_help`
Reports the server's live configuration (API key status, active model, absolute output directory) and a full reference of every exposed tool. Takes no arguments — call it first when diagnosing setup issues.

---

## 🐳 Docker

The MCP server is published to Docker Hub as
[`xbill9/nb2lite-agent`](https://hub.docker.com/r/xbill9/nb2lite-agent)
(tags: `latest`, `0.1.1`; `linux/amd64`). The image contains **only** the
FastMCP server and its open-source dependencies — no Claude Code, no API keys —
so nothing needs to be installed on the host except Docker itself.

> [!NOTE]
> This is a third-party community project, not affiliated with or endorsed by
> Anthropic or Google. You supply your own Gemini API key.

### Quick sanity check

```bash
docker pull xbill9/nb2lite-agent
docker run --rm -i -e GEMINI_API_KEY=dummy xbill9/nb2lite-agent
# The server is now waiting for MCP JSON-RPC on stdin (Ctrl-C to exit).
```

### Use it from Claude Code

The server saves images to disk and reads local files for `edit_local_image`,
so the container must see your project directory **at the same absolute path**
as the host — otherwise the tools report container paths that don't exist on
your machine. Mount it with `-v "$PWD:$PWD" -w "$PWD"`:

```bash
claude mcp add nb2lite-agent --env GEMINI_API_KEY="$(cat ~/gemini.key)" -- \
  docker run --rm -i -e GEMINI_API_KEY -v "$PWD:$PWD" -w "$PWD" xbill9/nb2lite-agent
```

Or hand-write the equivalent `.mcp.json` entry (replace `/abs/path/to/project`):

```json
{
  "mcpServers": {
    "nb2lite-agent": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "GEMINI_API_KEY",
        "-v", "/abs/path/to/project:/abs/path/to/project",
        "-w", "/abs/path/to/project",
        "xbill9/nb2lite-agent"
      ],
      "env": { "GEMINI_API_KEY": "your-key-here" }
    }
  }
}
```

The bare `-e GEMINI_API_KEY` (no value) forwards the variable from the `env`
block into the container without ever putting the key in the argument list.
Add `-e GEMINI_MODEL_NAME` / `-e IMAGE_OUTPUT_DIR` the same way to override
the model or redirect saved images (the path must be under the mount).
Restart Claude Code and approve the server; `/mcp` should list `nb2lite-agent`.

### Build and publish (maintainers)

```bash
make docker-build   # xbill9/nb2lite-agent:0.1.1 + :latest from server.py + requirements.txt
make docker-push    # build + push both tags (requires docker login)
```

`.dockerignore` whitelists only `server.py` and `requirements.txt`, so
key-carrying files (`.env`, `.mcp.json`) can never enter the build context.
The published image is currently `linux/amd64`; on an arm64 host (Apple
Silicon) Docker runs it under emulation, or build natively with
`docker build -t nb2lite-agent .` from a checkout.

---

## 🛠️ Development & Commands

Use the [Makefile](Makefile) to streamline common workflows:

| Command | Description |
| :--- | :--- |
| `make install` | Installs Python requirements. |
| `make run` | Starts the FastMCP server. |
| `make test` | Runs the full suite of agent integration tests. |
| `make lint` | Style and formatting checks (`ruff`) plus `bash -n` on the shell scripts. |
| `make clean` | Cleans up local Python cache files. |
| `make skill` | Refreshes all skill snapshots (`mcp/`, `.claude/skills/`, plugin copy in `skills/`) from the root sources. |
| `make skill-install` | Refreshes + copies the skill to `~/.claude/skills` (all projects). |
| `make skill-package` | Refreshes + rebuilds `dist/nb2lite-image-skill.zip`. |
| `make init` | Refreshes + installs the Claude skill into a target project and registers the MCP server (`TARGET=/path ARGS='...'`). |
| `make docker-build` | Builds the `xbill9/nb2lite-agent` Docker image (version + `latest` tags). |
| `make docker-push` | Builds + pushes both image tags to Docker Hub. |

---

## 🧩 Claude Skill

This repository is also packaged as a Claude Code skill named **`nb2lite-image`**:

- [SKILL.md](SKILL.md) — the skill manifest: workflow, MCP tool catalog, parameter constraints, and best practices.
- `mcp/` — the bundled FastMCP server snapshot, its requirements, and `project-setup.sh` (the one-command installer).
- `references/` — the Interactions API developer guide bundled with the skill.

Install into a project (copies the skill into `<project>/.claude/skills/nb2lite-image/` and registers the `nb2lite-agent` server in the project's `.mcp.json`):

```bash
make init TARGET=/path/to/project           # one project
make init ARGS='--global'                   # all projects (user scope)
mcp/project-setup.sh --help                 # all options
```

The installer reuses `~/gemini.key` (written by `set_env.sh`) when present. Restart Claude Code in the target project afterwards; `/mcp` should list `nb2lite-agent`.

> [!NOTE]
> `mcp/server.py` is a snapshot of the repo-root [server.py](server.py); the root copy is authoritative if the two differ. Run `make skill` after editing the sources to refresh every snapshot (`mcp/`, `.claude/skills/nb2lite-image/`, and the plugin copy in `skills/`) — never edit a snapshot directly.

### Plugin marketplace

The repo is also packaged as a Claude Code plugin (`.claude-plugin/plugin.json` + `marketplace.json`), which installs the skill **and** auto-registers the `nb2lite-agent` MCP server:

```
/plugin marketplace add xbill9/nb2lite-skill-claude
/plugin install nb2lite-image@nb2lite-skill-claude
```

The plugin manifest carries no API key — the server reads `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) from the environment, so run `source set_env.sh` first. Validate manifest changes with `claude plugin validate .`; a standalone zip of the skill is kept at `dist/nb2lite-image-skill.zip` (rebuild with `make skill-package`).

---

## 📚 Documentation

- [GEMINI.md](GEMINI.md) - Complete Interactions API developer guide, Python SDK walkthrough, and raw API specifications.
- [SKILL.md](SKILL.md) - Claude skill manifest for the `nb2lite-image` skill.
- [CLAUDE.md](CLAUDE.md) - Contributor guide for Claude Code: repository layout, the snapshot sync model, and coding standards.
- [references/gemini-interactions-api.md](references/gemini-interactions-api.md) - The Interactions API guide bundled with the skill (vendored; tracked in [skills-lock.json](skills-lock.json)).
- [devto-article.md](devto-article.md) - dev.to post covering the repo (background, Interactions API, MCP, skill install, examples); the cover image ([devto-cover.jpg](devto-cover.jpg)) was generated with this repo's own `generate_image` tool.
- [LICENSE](LICENSE) - Apache-2.0.
