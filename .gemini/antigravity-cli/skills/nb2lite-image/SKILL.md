---
name: nb2lite-image
description: Generate and edit images with Google's gemini-3.1-flash-lite-image (NB2Lite) via the stateful Interactions API. Use when the user asks to generate, edit, refine, or iterate on images, do multi-turn image editing with interaction IDs, edit a local image file, tune aspect ratio or thinking level, or set up/debug the NB2Lite MCP agent. Triggers include "generate an image", "edit this image", "nb2lite", "flash-lite-image", "Interactions API", "interaction id", "aspect ratio", "thinking level".
---

# NB2Lite Image Generation

Generate and iteratively edit images with `gemini-3.1-flash-lite-image` — Google's
high-efficiency image model with sub-2-second generations and stateful multi-turn
editing via the Interactions API. Two ways to act:

1. **Preferred — MCP agent tools.** If the `nb2lite-agent` MCP server is connected
   in this session, use its tools (catalog below). They wrap the Interactions API
   calls with input validation, mime-type detection, and concurrency-safe file
   saving.
2. **Fallback — direct SDK.** If the MCP server is not connected, either offer to
   register the bundled server (see "Registering the MCP server") or call the
   Interactions API directly with the `google-genai` Python SDK using the examples
   in `references/gemini-interactions-api.md`.

## Bundled files

- `mcp/server.py` — the FastMCP NB2Lite agent (snapshot of the repo-root
  `server.py`; the live copy at the repo root is authoritative if the two differ).
- `mcp/requirements.txt` — Python dependencies (`google-genai`, `mcp`).
- `mcp/project-setup.sh` — one-command installer: copies this skill into a target
  project or globally into `~/.gemini/antigravity-cli/skills/` and registers the MCP server.
- `references/gemini-interactions-api.md` — the Interactions API developer guide:
  stateful vs. stateless architecture, parameter cheat sheet, Python SDK examples,
  best practices for multi-turn editing. Read it when working without the MCP
  tools, composing raw SDK calls, or answering API questions.

## Registering the MCP server

Easiest path — run the bundled installer (idempotent; installs this skill into the
target project or globally and writes the `nb2lite-agent` entry into the `.mcp.json`,
using system `python3`):

```bash
mcp/project-setup.sh /path/to/project                    # one project
mcp/project-setup.sh --global                            # all projects (user scope: ~/.gemini/antigravity-cli/skills)
# from the skill repo root: make init TARGET=/path/to/project ARGS='--model <name>'
```

Run `mcp/project-setup.sh --help` for all options (`--model`, `--output-dir`,
`--server-name`, `--skip-deps`). Then restart Antigravity CLI in the target project.

Manual alternative:

```bash
python3 mcp/server.py
```

Requires: `pip install -r mcp/requirements.txt` and a Gemini API key. The server
reads config from env vars: `GEMINI_API_KEY` (or `GOOGLE_API_KEY` fallback),
`GEMINI_MODEL_NAME` (default `gemini-3.1-flash-lite-image`), and
`IMAGE_OUTPUT_DIR` (default `.`). The repo-root `set_env.sh` helper reads or
prompts for the key, persists it to `~/gemini.key`, writes `.env`, and patches an
existing `.mcp.json` entry — the installer reuses `~/gemini.key` automatically
when present.

## Standard workflow

1. **Config first.** `get_help` reports whether an API key is set, the active
   model, and the output directory. If the key is missing, stop and have the user
   run `set_env.sh` (or export `GEMINI_API_KEY`) — every other tool will fail
   without it.
2. **Generate.** `generate_image(prompt, aspect_ratio, thinking_level)` creates a
   1k-resolution image, saves it locally, and returns the saved path plus an
   **interaction ID**. Every call sets `store=True`, so the visual context
   persists on Google's servers for follow-up edits.
3. **Iterate statefully.** `edit_image(previous_interaction_id, edit_prompt)`
   applies incremental changes while preserving character, style, and pixel
   continuity. Each edit returns a **new** interaction ID — always chain the most
   recent one into the next edit, not the original.
4. **Edit local files.** `edit_local_image(image_path, edit_prompt)` uploads an
   existing image inline as base64 and applies the described edit — use it for
   files that did not come from a prior interaction. It too returns an interaction
   ID, so subsequent refinements should switch to `edit_image`.
5. **Deliver.** Outputs land in `IMAGE_OUTPUT_DIR` as
   `<prefix>_<timestamp>_<uuid8>.<ext>` (`gen_`, `edit_`, or `edit_local_`
   prefix; extension follows the returned mime type — png/jpg/webp). Report the
   absolute saved path back to the user.

## MCP tool catalog (by task)

**Generation:** `generate_image` (text → image; saves locally, returns
interaction ID)

**Editing:** `edit_image` (stateful multi-turn edit by interaction ID),
`edit_local_image` (inline base64 upload of a local file + edit prompt)

**Diagnostics:** `get_help` (live configuration: key status, model name, output
directory, full tool reference)

## Parameter constraints

Validated by the server — out-of-range values fail fast:

- **Aspect ratios:** `1:1` (default), `16:9`, `9:16`, `4:3`, `3:4`.
  `edit_image` takes no aspect ratio — stateful edits keep the previous turn's.
- **Thinking levels:** `low` (default), `high`. Use `low` for fast previews and
  prototyping; `high` for complex rendering, accurate text layout, or character
  composition. (The generic Interactions API spec also lists `minimal` and
  `medium`, but the live API rejects them for this model with HTTP 400.)

## Best practices & cautions

- **Keep edit prompts incremental.** Describe only the change ("make the sky dark
  blue with lightning"), not the whole scene again — the interaction context
  already holds the rest.
- **Don't change aspect ratio mid-session.** Switching ratios between stateful
  turns degrades pixel continuity; pick the ratio at generation time.
- **Chain the latest interaction ID.** Editing from a stale ID silently forks the
  session from an older state.
- **Tool errors return as text.** Failures come back as `🔴 ...` strings rather
  than protocol errors — check for them before reporting success. A missing-key
  failure means the server process needs the env vars set and a restart.
- **Generated images are billable API calls** — batch related edits into one
  well-specified prompt when the user cares about cost, and prefer lower thinking
  levels for drafts.
- **Never commit secrets.** `.env`, `~/gemini.key`, and `.mcp.json` (which may
  carry injected keys) are gitignored here — keep it that way in target projects.
