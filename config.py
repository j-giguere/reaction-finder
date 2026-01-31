"""Configuration for Reaction Finder application."""

import os


class Config:
    """Application configuration with environment variable support."""

    # Ollama settings
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    # Fallback image when Ollama fails or returns invalid response
    FALLBACK_IMAGE_ID = os.getenv("FALLBACK_IMAGE_ID", "yea-creature")

    # LLM generation settings
    OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.3"))
