"""Vision LLM service for automatic metadata generation from images."""

import base64
import json
import logging
import re
from pathlib import Path
from typing import BinaryIO

import httpx
import ollama
from ollama import ResponseError

from config import Config

logger = logging.getLogger(__name__)


class MetadataGenerationError(Exception):
    """Raised when metadata generation fails."""
    pass

METADATA_PROMPT = """Describe this reaction image in JSON format.

What is shown in the image? What emotion or situation would someone use this for?

Respond with ONLY this JSON (no other text):
{"description": "SHORT DESCRIPTION - use when SITUATION", "tags": ["emotion", "topic", "action"]}"""


class MetadataGenerator:
    """Service that uses vision LLM to generate metadata for reaction images."""

    def __init__(self, timeout: float = 120.0):
        """Initialize the metadata generator with vision model."""
        self.model = Config.VISION_MODEL
        self.host = Config.OLLAMA_HOST
        self.timeout = timeout
        # Set timeout on the client to prevent hanging indefinitely
        self._client = ollama.Client(host=self.host, timeout=timeout)

    def _encode_image(self, file: BinaryIO) -> str:
        """Encode image file to base64 string."""
        file.seek(0)
        return base64.b64encode(file.read()).decode("utf-8")

    def _encode_image_from_path(self, image_path: Path) -> str:
        """Encode image file from path to base64 string."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _parse_json_response(self, response_text: str) -> dict | None:
        """Parse JSON from LLM response, handling various malformed outputs."""
        # Try to extract JSON from markdown code block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response_text)
        if json_match:
            response_text = json_match.group(1).strip()

        # Try direct JSON parse
        try:
            parsed = json.loads(response_text)
            # Handle case where LLM returns array instead of object
            if isinstance(parsed, list) and len(parsed) > 0:
                parsed = parsed[0]
            return parsed
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in the response
        json_match = re.search(r"\{[\s\S]*?\}", response_text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Fallback: try to extract description from plain text
        logger.warning(f"Attempting fallback parsing for response: {response_text[:200]}")
        return self._fallback_parse(response_text)

    def _fallback_parse(self, response_text: str) -> dict | None:
        """Attempt to extract metadata from non-JSON responses."""
        # Clean up the response
        text = response_text.strip()

        # Try to extract any quoted strings as description
        quotes = re.findall(r'"([^"]+)"', text)
        if quotes:
            # Use longest quoted string as description
            description = max(quotes, key=len)
            # Use other short strings as tags
            tags = [q.lower() for q in quotes if q != description and len(q) < 30]
            if not tags:
                tags = ["reaction", "meme"]
            return {"description": description, "tags": tags[:8]}

        # Last resort: use the raw text as description
        if len(text) > 10 and len(text) < 500:
            return {
                "description": text[:200].replace("\n", " ").strip(),
                "tags": ["reaction", "meme"]
            }

        logger.error(f"Failed to parse response: {response_text}")
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
            logger.info(f"Sending image to vision model {self.model} for analysis...")

            response = self._client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": METADATA_PROMPT,
                        "images": [image_b64],
                    }
                ],
                options={
                    "temperature": 0.3,
                    "num_predict": 256,  # Limit response length for speed
                },
            )

            response_text = response["message"]["content"]
            logger.info(f"Vision LLM response received")
            logger.debug(f"Vision LLM response: {response_text}")

            metadata = self._parse_json_response(response_text)

            if metadata and "description" in metadata and "tags" in metadata:
                # Ensure tags is a list
                if isinstance(metadata["tags"], str):
                    metadata["tags"] = [t.strip() for t in metadata["tags"].split(",")]
                return metadata

            logger.warning("Invalid metadata format from LLM response")
            raise MetadataGenerationError("Failed to parse metadata from LLM response")

        except httpx.TimeoutException:
            logger.error(f"Timeout waiting for vision model (>{self.timeout}s)")
            raise MetadataGenerationError("Image analysis timed out. Try a smaller image or try again later.")
        except ResponseError as e:
            logger.error(f"Ollama API error: {e}")
            raise MetadataGenerationError(f"Failed to analyze image: {e}")
        except MetadataGenerationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating metadata: {e}")
            raise MetadataGenerationError(f"Failed to generate metadata: {e}")

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
            logger.info(f"Sending image to vision model {self.model} for analysis...")

            response = self._client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": METADATA_PROMPT,
                        "images": [image_b64],
                    }
                ],
                options={
                    "temperature": 0.3,
                    "num_predict": 256,  # Limit response length for speed
                },
            )

            response_text = response["message"]["content"]
            logger.info(f"Vision LLM response received")
            logger.debug(f"Vision LLM response: {response_text}")

            metadata = self._parse_json_response(response_text)

            if metadata and "description" in metadata and "tags" in metadata:
                if isinstance(metadata["tags"], str):
                    metadata["tags"] = [t.strip() for t in metadata["tags"].split(",")]
                return metadata

            logger.warning("Invalid metadata format from LLM response")
            raise MetadataGenerationError("Failed to parse metadata from LLM response")

        except httpx.TimeoutException:
            logger.error(f"Timeout waiting for vision model (>{self.timeout}s)")
            raise MetadataGenerationError("Image analysis timed out. Try a smaller image or try again later.")
        except ResponseError as e:
            logger.error(f"Ollama API error: {e}")
            raise MetadataGenerationError(f"Failed to analyze image: {e}")
        except MetadataGenerationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating metadata: {e}")
            raise MetadataGenerationError(f"Failed to generate metadata: {e}")

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
