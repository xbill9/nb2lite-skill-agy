import os
import base64
import time
import logging
import mimetypes
import uuid
import sys
from typing import Any, cast
from google import genai
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("NB2Lite Agent")

# Configure Logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("nb2lite-agent")

# Global client reference, lazily initialized
client = None
MODEL_NAME = os.environ.get("GEMINI_MODEL_NAME", "gemini-3.1-flash-lite-image")

# Validation Constraints
SUPPORTED_ASPECT_RATIOS = {"1:1", "16:9", "9:16", "4:3", "3:4"}
SUPPORTED_THINKING_LEVELS = {"low", "high"}


def _get_client() -> genai.Client:
    """Helper to lazily initialize or retrieve the Gemini Client.

    Supports both GEMINI_API_KEY and the GOOGLE_API_KEY fallback.
    """
    global client
    if client is None:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY or GOOGLE_API_KEY environment variable is missing. "
                "Please set it and restart the server."
            )
        client = genai.Client(api_key=api_key)
    return client


def _validate_inputs(
    aspect_ratio: str | None = None, thinking_level: str | None = None
) -> None:
    """Validate that parameters conform to the gemini-3.1-flash-lite-image model constraints."""
    if aspect_ratio and aspect_ratio not in SUPPORTED_ASPECT_RATIOS:
        raise ValueError(
            f"Unsupported aspect ratio '{aspect_ratio}'. "
            f"Supported ratios: {', '.join(sorted(SUPPORTED_ASPECT_RATIOS))}"
        )
    if thinking_level and thinking_level.lower() not in SUPPORTED_THINKING_LEVELS:
        raise ValueError(
            f"Unsupported thinking level '{thinking_level}'. "
            f"Supported levels: {', '.join(sorted(SUPPORTED_THINKING_LEVELS))}"
        )


def _get_image_data(image_path: str) -> dict:
    """Helper to convert local image file to base64 input dict.

    Uses robust mime-type detection.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at path: {image_path}")

    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or not mime_type.startswith("image/"):
        # Fallback guess for common extensions
        if image_path.lower().endswith((".jpg", ".jpeg")):
            mime_type = "image/jpeg"
        elif image_path.lower().endswith(".webp"):
            mime_type = "image/webp"
        else:
            mime_type = "image/png"

    with open(image_path, "rb") as f:
        data_b64 = base64.b64encode(f.read()).decode("utf-8")

    return {"type": "image", "data": data_b64, "mime_type": mime_type}


def _handle_response(interaction: Any, output_prefix: str) -> str:
    """Helper to decode base64 image data and save the resulting image."""
    image_output = getattr(interaction, "output_image", None)
    if not image_output:
        return (
            f"🟢 Interaction completed successfully.\n"
            f"• Interaction ID: {interaction.id}\n"
            f"• Note: No direct image output was found in the response."
        )

    ext = "jpg"
    mime_type = getattr(image_output, "mime_type", "")
    if "png" in mime_type:
        ext = "png"
    elif "webp" in mime_type:
        ext = "webp"

    # Use UUID to ensure unique filenames under high concurrency
    unique_id = uuid.uuid4().hex[:8]
    output_filename = f"{output_prefix}_{int(time.time())}_{unique_id}.{ext}"

    # Allow setting a custom output directory from environment
    output_dir = os.environ.get("IMAGE_OUTPUT_DIR", ".")
    if output_dir != ".":
        os.makedirs(output_dir, exist_ok=True)

    full_output_path = os.path.join(output_dir, output_filename)

    data = getattr(image_output, "data", None)
    if not data:
        raise ValueError("No image data found in output_image.")

    if isinstance(data, str):
        image_bytes = base64.b64decode(data)
    else:
        image_bytes = data

    with open(full_output_path, "wb") as f:
        f.write(image_bytes)

    return (
        f"🟢 Image successfully saved!\n"
        f"• Saved to: {os.path.abspath(full_output_path)}\n"
        f"• Interaction ID: {interaction.id}"
    )


@mcp.tool()
def generate_image(
    prompt: str, aspect_ratio: str = "1:1", thinking_level: str = "low"
) -> str:
    """Generates a new image from a text prompt.

    - prompt: The text description of the image.
    - aspect_ratio: Aspect ratio of the output image ('1:1', '16:9', '9:16', '4:3', '3:4').
    - thinking_level: The amount of thought tokens to generate ('low', 'high').
    """
    try:
        _validate_inputs(aspect_ratio=aspect_ratio, thinking_level=thinking_level)

        response_format = {"type": "image"}
        if aspect_ratio:
            response_format["aspect_ratio"] = aspect_ratio

        generation_config = {}
        if thinking_level:
            generation_config["thinking_level"] = thinking_level.lower()

        ai_client = _get_client()
        interaction = ai_client.interactions.create(
            model=MODEL_NAME,
            input=prompt,
            response_format=cast(Any, response_format),
            generation_config=cast(Any, generation_config),
            store=True,
        )

        return _handle_response(interaction, "gen")
    except Exception as e:
        logger.exception("Image generation failed")
        return f"🔴 Image generation failed: {str(e)}"


@mcp.tool()
def edit_image(
    previous_interaction_id: str,
    edit_prompt: str,
    thinking_level: str = "low",
) -> str:
    """Edits a previously generated image using its interaction ID.

    The model maintains contextual elements while applying your edit.
    - previous_interaction_id: The ID from the previous turn.
    - edit_prompt: Natural language description of what to change in the image.
    - thinking_level: The amount of thought tokens to generate ('low', 'high').
    """
    try:
        _validate_inputs(thinking_level=thinking_level)

        response_format = {"type": "image"}

        generation_config = {}
        if thinking_level:
            generation_config["thinking_level"] = thinking_level.lower()

        ai_client = _get_client()
        interaction = ai_client.interactions.create(
            model=MODEL_NAME,
            previous_interaction_id=previous_interaction_id,
            input=edit_prompt,
            response_format=cast(Any, response_format),
            generation_config=cast(Any, generation_config),
            store=True,
        )

        return _handle_response(interaction, "edit")
    except Exception as e:
        logger.exception("Editing failed")
        return f"🔴 Editing failed: {str(e)}"


@mcp.tool()
def edit_local_image(
    image_path: str,
    edit_prompt: str,
    aspect_ratio: str = "1:1",
    thinking_level: str = "low",
) -> str:
    """Edits a local image using a text prompt description.

    - image_path: Path to the local image file.
    - edit_prompt: Natural language description of how to edit or modify the image.
    - aspect_ratio: Aspect ratio of the output image ('1:1', '16:9', '9:16', '4:3', '3:4').
    - thinking_level: The amount of thought tokens to generate ('low', 'high').
    """
    try:
        _validate_inputs(aspect_ratio=aspect_ratio, thinking_level=thinking_level)
        img_data = _get_image_data(image_path)

        response_format = {"type": "image"}
        if aspect_ratio:
            response_format["aspect_ratio"] = aspect_ratio

        generation_config = {}
        if thinking_level:
            generation_config["thinking_level"] = thinking_level.lower()

        ai_client = _get_client()
        interaction = ai_client.interactions.create(
            model=MODEL_NAME,
            input=cast(Any, [img_data, {"type": "text", "text": edit_prompt}]),
            response_format=cast(Any, response_format),
            generation_config=cast(Any, generation_config),
            store=True,
        )

        return _handle_response(interaction, "edit_local")
    except Exception as e:
        logger.exception("Local image edit failed")
        return f"🔴 Local image edit failed: {str(e)}"


@mcp.tool()
def get_help() -> str:
    """Provides help text and summarizes the configuration options and all available image generation/editing tools for this MCP server."""
    gemini_key_status = (
        "Set"
        if (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
        else "Not Set"
    )
    image_output_dir = os.environ.get("IMAGE_OUTPUT_DIR", ".")

    return (
        "### 🌌 NB2Lite Agent (gemini-3.1-flash-lite-image) Help & Configuration\n\n"
        "This MCP server interfaces with the stateful **Interactions API** using the Google GenAI SDK to generate and edit images via the high-efficiency **`gemini-3.1-flash-lite-image`** model.\n\n"
        "#### ⚙️ Configuration Options (Environment Variables)\n"
        f"- **`GEMINI_API_KEY` / `GOOGLE_API_KEY`**: API keys used to authenticate with Gemini.\n"
        f"  - *Current Status:* `{gemini_key_status}`\n"
        f"- **`GEMINI_MODEL_NAME`**: The name of the interactions model to use.\n"
        f"  - *Current Value:* `{MODEL_NAME}`\n"
        f"- **`IMAGE_OUTPUT_DIR`**: The directory where generated and edited images are stored.\n"
        f"  - *Current Value:* `{os.path.abspath(image_output_dir)}`\n\n"
        "#### 🧰 Available MCP Tools\n\n"
        "Below is a summary of the tools exposed by this agent:\n\n"
        "##### 🎨 Image Generation & Editing\n"
        "- **`generate_image`**: Generates a new image from a text prompt and saves it locally.\n"
        "  - *Arguments*:\n"
        "    - `prompt` (str, required): Natural language description of the image.\n"
        "    - `aspect_ratio` (str, optional): Output ratio (default: `'1:1'`). Supported: `1:1`, `16:9`, `9:16`, `4:3`, `3:4`.\n"
        "    - `thinking_level` (str, optional): Latency vs. quality steps (default: `'low'`). Supported: `low`, `high`.\n"
        "- **`edit_image`**: Edits a previously generated image using its interaction ID, maintaining continuity.\n"
        "  - *Arguments*:\n"
        "    - `previous_interaction_id` (str, required): The unique interaction ID returned from the previous turn.\n"
        "    - `edit_prompt` (str, required): Natural language description of changes/additions to apply.\n"
        "    - `thinking_level` (str, optional): Latency vs. quality steps (default: `'low'`). Supported: `low`, `high`.\n"
        "- **`edit_local_image`**: Uploads a local image file in-line via Base64 and describes edits to apply.\n"
        "  - *Arguments*:\n"
        "    - `image_path` (str, required): Path to the local image file.\n"
        "    - `edit_prompt` (str, required): Natural language description of modifications to apply.\n"
        "    - `aspect_ratio` (str, optional): Output ratio (default: `'1:1'`). Supported: `1:1`, `16:9`, `9:16`, `4:3`, `3:4`.\n"
        "    - `thinking_level` (str, optional): Latency vs. quality steps (default: `'low'`). Supported: `low`, `high`.\n"
        "- **`get_help`**: Provides this help text and summarizes the server configuration and available tools.\n\n"
        "#### 💾 File Output & Stateful Session Management\n"
        "- All successful generation and edit requests save the output image locally under `IMAGE_OUTPUT_DIR` using a concurrent-safe naming format: `<prefix>_<timestamp>_<uuid_hex>.<extension>` (e.g. `gen_1780123456_a3b2c1d0.png`).\n"
        "- Each API call sets `store=True` by default, generating a persistent `interaction_id` session context on Google's servers. Pass this ID as `previous_interaction_id` in subsequent `edit_image` calls to perform multi-turn modifications with high character, style, and pixel continuity."
    )


if __name__ == "__main__":
    mcp.run()
