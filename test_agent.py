import unittest
import os
import tempfile
from unittest.mock import MagicMock, patch

# Import functions to test from server
from server import _get_image_data, generate_image, edit_image, mcp


class TestNB2LiteAgent(unittest.TestCase):
    def setUp(self):
        # Create a temporary file for image tests
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_image_path = os.path.join(self.test_dir.name, "test.png")
        # Write dummy png bytes
        with open(self.test_image_path, "wb") as f:
            f.write(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            )

    def tearDown(self):
        self.test_dir.cleanup()

    def test_get_image_data_valid(self):
        """Test image encoding helper with a valid image file."""
        data = _get_image_data(self.test_image_path)
        self.assertEqual(data["type"], "image")
        self.assertEqual(data["mime_type"], "image/png")
        self.assertTrue(len(data["data"]) > 0)

    def test_get_image_data_missing(self):
        """Test image encoding helper raises FileNotFoundError if file is missing."""
        with self.assertRaises(FileNotFoundError):
            _get_image_data("non_existent_file.png")

    @patch("server._get_client")
    def test_generate_image_success(self, mock_get_client):
        """Test generate_image tool with mocked Interactions API response."""
        mock_client = MagicMock()
        mock_interaction = MagicMock()
        mock_interaction.id = "int_123"
        mock_interaction.output_image = MagicMock()
        mock_interaction.output_image.mime_type = "image/png"
        mock_interaction.output_image.data = b"dummy_png_bytes"
        mock_client.interactions.create.return_value = mock_interaction
        mock_get_client.return_value = mock_client

        with patch("server.open", unittest.mock.mock_open()):
            result = generate_image(
                prompt="test prompt",
                aspect_ratio="1:1",
                thinking_level="medium",
            )
            self.assertIn("🟢 Image successfully saved!", result)
            self.assertIn("int_123", result)

    @patch("server._get_client")
    def test_generate_image_no_output_image(self, mock_get_client):
        """Test generate_image tool when no output image is returned by the API."""
        mock_client = MagicMock()
        mock_interaction = MagicMock()
        mock_interaction.id = "int_123"
        mock_interaction.output_image = None
        mock_client.interactions.create.return_value = mock_interaction
        mock_get_client.return_value = mock_client

        result = generate_image(
            prompt="test prompt", aspect_ratio="1:1", thinking_level="medium"
        )
        self.assertIn("🟢 Interaction completed successfully.", result)
        self.assertIn("No direct image output was found", result)

    @patch("server._get_client")
    def test_generate_image_failure(self, mock_get_client):
        """Test generate_image tool gracefully handles exceptions."""
        mock_client = MagicMock()
        mock_client.interactions.create.side_effect = Exception("API Key expired")
        mock_get_client.return_value = mock_client

        result = generate_image(prompt="test prompt")
        self.assertIn("🔴 Image generation failed: API Key expired", result)

    @patch("server._get_client")
    def test_edit_image_success(self, mock_get_client):
        """Test edit_image tool with mocked Interactions API response."""
        mock_client = MagicMock()
        mock_interaction = MagicMock()
        mock_interaction.id = "int_456"
        mock_interaction.output_image = MagicMock()
        mock_interaction.output_image.mime_type = "image/jpeg"
        # Use a valid base64-encoded string
        mock_interaction.output_image.data = "ZHVtbXlfanBlZ19iYXNlNjRfc3RyaW5n"
        mock_client.interactions.create.return_value = mock_interaction
        mock_get_client.return_value = mock_client

        with patch("server.open", unittest.mock.mock_open()):
            result = edit_image(
                previous_interaction_id="int_123", edit_prompt="add stars"
            )
            self.assertIn("🟢 Image successfully saved!", result)
            self.assertIn("int_456", result)

    def test_mcp_tools_registered(self):
        """Verify that the expected tools are registered to the FastMCP server."""
        tools = [t.name for t in mcp._tool_manager.list_tools()]
        self.assertIn("generate_image", tools)
        self.assertIn("edit_image", tools)
        self.assertIn("edit_local_image", tools)
        self.assertIn("get_help", tools)

    def test_get_help(self):
        """Verify that get_help returns correct info containing the available tools and variables."""
        from server import get_help

        result = get_help()
        self.assertIn("generate_image", result)
        self.assertIn("edit_image", result)
        self.assertIn("edit_local_image", result)
        self.assertIn("get_help", result)
        self.assertIn("GEMINI_MODEL_NAME", result)

    def test_validation_invalid_aspect_ratio(self):
        """Verify that validation fails for invalid aspect ratios."""
        result = generate_image(prompt="test", aspect_ratio="21:9")
        self.assertIn("Unsupported aspect ratio '21:9'", result)

    def test_validation_invalid_thinking_level(self):
        """Verify that validation fails for invalid thinking levels."""
        result = generate_image(prompt="test", thinking_level="ultra")
        self.assertIn("Unsupported thinking level 'ultra'", result)


if __name__ == "__main__":
    unittest.main()
