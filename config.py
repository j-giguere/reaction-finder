"""Configuration for Reaction Finder application."""

import os


class Config:
    """Application configuration with environment variable support."""

    # Ollama settings
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    # Vision model for metadata generation (llava or llama3.2-vision)
    VISION_MODEL = os.getenv("VISION_MODEL", "llava")

    # Fallback image when Ollama fails or returns invalid response
    FALLBACK_IMAGE_ID = os.getenv("FALLBACK_IMAGE_ID", "yea-creature")

    # LLM generation settings
    OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.3"))

    # Upload settings
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 10 * 1024 * 1024))  # 10MB default
    ALLOWED_EXTENSIONS = {"jpeg", "jpg", "png", "gif", "webp"}
