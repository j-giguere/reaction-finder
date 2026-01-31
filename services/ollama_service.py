"""Ollama LLM service for intelligent reaction image selection."""

import logging
from typing import Optional

import ollama
from ollama import ResponseError

from config import Config

logger = logging.getLogger(__name__)


class OllamaService:
    """Service that wraps Ollama LLM for selecting reaction images."""

    def __init__(self, image_catalog: dict):
        """
        Initialize the Ollama service.

        Args:
            image_catalog: Dictionary containing image data with 'images' key
        """
        self.model = Config.OLLAMA_MODEL
        self.host = Config.OLLAMA_HOST
        self.temperature = Config.OLLAMA_TEMPERATURE
        self.fallback_id = Config.FALLBACK_IMAGE_ID

        # Store image catalog and build lookup
        self.images = image_catalog.get("images", [])
        self.valid_ids = {img["id"] for img in self.images}

        # Build the system prompt once at initialization
        self._system_prompt = self._build_system_prompt()

        # Configure ollama client
        self._client = ollama.Client(host=self.host)

    def _build_system_prompt(self) -> str:
        """Build the system prompt with all available reaction images."""
        image_descriptions = []
        for img in self.images:
            tags_str = ", ".join(img.get("tags", []))
            image_descriptions.append(
                f"- ID: {img['id']}\n"
                f"  Description: {img['description']}\n"
                f"  Tags: {tags_str}"
            )

        images_text = "\n".join(image_descriptions)

        return f"""You are a reaction image selector. Given a user's message, select the most appropriate reaction image from the catalog below.

IMPORTANT: Respond with ONLY the image ID, nothing else. No explanation, no punctuation, just the exact ID.

Available reaction images:
{images_text}

Remember: Your response must be ONLY the image ID exactly as shown above."""

    def _parse_response(self, response_text: str) -> Optional[str]:
        """
        Parse the LLM response to extract a valid image ID.

        Args:
            response_text: Raw response from the LLM

        Returns:
            Valid image ID if found, None otherwise
        """
        # Clean up the response - remove whitespace and common artifacts
        cleaned = response_text.strip().lower()

        # Sometimes LLM might wrap in quotes or add punctuation
        cleaned = cleaned.strip("\"'`.,!?")

        # Check if it's a valid ID
        if cleaned in self.valid_ids:
            return cleaned

        # Try to find a valid ID within the response (in case LLM added extra text)
        for valid_id in self.valid_ids:
            if valid_id in cleaned:
                logger.warning(
                    f"Found ID '{valid_id}' embedded in response: '{response_text}'"
                )
                return valid_id

        logger.warning(f"Could not parse valid image ID from response: '{response_text}'")
        return None

    def select_image(self, prompt: str) -> str:
        """
        Use the LLM to select the most appropriate reaction image for the prompt.

        Args:
            prompt: User's text prompt describing the reaction they want

        Returns:
            Image ID of the selected reaction image (fallback ID if LLM fails)
        """
        if not prompt or not prompt.strip():
            logger.warning("Empty prompt received, returning fallback image")
            return self.fallback_id

        try:
            response = self._client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": prompt},
                ],
                options={"temperature": self.temperature},
            )

            response_text = response["message"]["content"]
            logger.debug(f"LLM response for '{prompt}': '{response_text}'")

            image_id = self._parse_response(response_text)
            if image_id:
                return image_id

            logger.warning(f"Invalid LLM response, using fallback: {self.fallback_id}")
            return self.fallback_id

        except ResponseError as e:
            logger.error(f"Ollama API error: {e}")
            return self.fallback_id
        except Exception as e:
            logger.error(f"Unexpected error calling Ollama: {e}")
            return self.fallback_id

    def is_available(self) -> bool:
        """
        Check if Ollama is running and the model is available.

        Returns:
            True if Ollama is healthy and model is loaded, False otherwise
        """
        try:
            # List models to check connection
            models = self._client.list()
            model_names = [m.get("name", "").split(":")[0] for m in models.get("models", [])]

            if self.model in model_names or f"{self.model}:latest" in [
                m.get("name", "") for m in models.get("models", [])
            ]:
                return True

            # Model might be available but with different tag
            for m in models.get("models", []):
                if m.get("name", "").startswith(self.model):
                    return True

            logger.warning(f"Model '{self.model}' not found in available models: {model_names}")
            return False

        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            return False
