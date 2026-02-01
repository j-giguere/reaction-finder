"""Vision LLM service for automatic metadata generation from images."""

import base64
import json
import logging
import re
from pathlib import Path
from typing import BinaryIO

import ollama
from ollama import ResponseError

from config import Config

logger = logging.getLogger(__name__)

METADATA_PROMPT = """You are analyzing a reaction image/meme. Generate metadata as JSON with exactly this structure:
{
  "description": "[Subject] [action] - use when [situation]",
  "tags": ["emotion1", "emotion2", "source", "action"]
}

Guidelines:
- Description should be concise and explain what the image shows and when to use it
- Tags should include: emotions conveyed, source material (if recognizable), actions shown
- Include 4-8 relevant tags
- Return ONLY valid JSON, no other text

Analyze this image and generate the metadata:"""


class MetadataGenerator:
    """Service that uses vision LLM to generate metadata for reaction images."""

    def __init__(self):
        """Initialize the metadata generator with vision model."""
        self.model = Config.VISION_MODEL
        self.host = Config.OLLAMA_HOST
        self._client = ollama.Client(host=self.host)

    def _encode_image(self, file: BinaryIO) -> str:
        """Encode image file to base64 string."""
        file.seek(0)
        return base64.b64encode(file.read()).decode("utf-8")

    def _encode_image_from_path(self, image_path: Path) -> str:
        """Encode image file from path to base64 string."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _parse_json_response(self, response_text: str) -> dict | None:
        """Parse JSON from LLM response, handling markdown code blocks."""
        # Try to extract JSON from markdown code block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response_text)
        if json_match:
            response_text = json_match.group(1).strip()

        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            logger.error(f"Failed to parse JSON from response: {response_text}")
            return None

    def generate_metadata(self, file: BinaryIO) -> dict:
        """
        Generate metadata for an uploaded image using vision LLM.

        Args:
            file: File-like object containing image data

        Returns:
            Dictionary with 'description' and 'tags' keys
        """
        try:
            image_b64 = self._encode_image(file)

            response = self._client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": METADATA_PROMPT,
                        "images": [image_b64],
                    }
                ],
                options={"temperature": 0.3},
            )

            response_text = response["message"]["content"]
            logger.debug(f"Vision LLM response: {response_text}")

            metadata = self._parse_json_response(response_text)

            if metadata and "description" in metadata and "tags" in metadata:
                # Ensure tags is a list
                if isinstance(metadata["tags"], str):
                    metadata["tags"] = [t.strip() for t in metadata["tags"].split(",")]
                return metadata

            logger.warning("Invalid metadata format, using defaults")
            return self._default_metadata()

        except ResponseError as e:
            logger.error(f"Ollama API error: {e}")
            return self._default_metadata()
        except Exception as e:
            logger.error(f"Unexpected error generating metadata: {e}")
            return self._default_metadata()

    def generate_metadata_from_path(self, image_path: Path) -> dict:
        """
        Generate metadata for an image file on disk.

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary with 'description' and 'tags' keys
        """
        try:
            image_b64 = self._encode_image_from_path(image_path)

            response = self._client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": METADATA_PROMPT,
                        "images": [image_b64],
                    }
                ],
                options={"temperature": 0.3},
            )

            response_text = response["message"]["content"]
            logger.debug(f"Vision LLM response: {response_text}")

            metadata = self._parse_json_response(response_text)

            if metadata and "description" in metadata and "tags" in metadata:
                if isinstance(metadata["tags"], str):
                    metadata["tags"] = [t.strip() for t in metadata["tags"].split(",")]
                return metadata

            logger.warning("Invalid metadata format, using defaults")
            return self._default_metadata()

        except ResponseError as e:
            logger.error(f"Ollama API error: {e}")
            return self._default_metadata()
        except Exception as e:
            logger.error(f"Unexpected error generating metadata: {e}")
            return self._default_metadata()

    def _default_metadata(self) -> dict:
        """Return default metadata when generation fails."""
        return {
            "description": "Reaction image - use when appropriate",
            "tags": ["reaction", "meme"],
        }

    def is_available(self) -> bool:
        """Check if the vision model is available."""
        try:
            models = self._client.list()
            model_names = [m.get("name", "").split(":")[0] for m in models.get("models", [])]

            if self.model in model_names:
                return True

            for m in models.get("models", []):
                if m.get("name", "").startswith(self.model):
                    return True

            logger.warning(f"Vision model '{self.model}' not found")
            return False

        except Exception as e:
            logger.error(f"Failed to check vision model availability: {e}")
            return False
