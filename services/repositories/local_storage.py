"""Local filesystem implementation for image storage."""

import logging
from pathlib import Path
from typing import BinaryIO

from .base import ImageStorageRepository

logger = logging.getLogger(__name__)


class LocalImageStorage(ImageStorageRepository):
    """Store images on the local filesystem."""

    def __init__(self, storage_dir: Path, url_prefix: str = "/static/images"):
        """
        Initialize local image storage.

        Args:
            storage_dir: Directory path where images will be stored
            url_prefix: URL prefix for serving images (default: /static/images)
        """
        self.storage_dir = Path(storage_dir)
        self.url_prefix = url_prefix.rstrip("/")

        # Ensure storage directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_image(self, file: BinaryIO, filename: str) -> str:
        """Save an image to the local filesystem."""
        file_path = self.storage_dir / filename

        try:
            with open(file_path, "wb") as f:
                # Read in chunks for memory efficiency
                while chunk := file.read(8192):
                    f.write(chunk)

            logger.info(f"Saved image to {file_path}")
            return self.get_image_url(filename)

        except IOError as e:
            logger.error(f"Failed to save image {filename}: {e}")
            raise

    def get_image_url(self, filename: str) -> str:
        """Get the URL for accessing an image."""
        return f"{self.url_prefix}/{filename}"

    def delete_image(self, filename: str) -> bool:
        """Delete an image from local storage."""
        file_path = self.storage_dir / filename

        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted image {filename}")
                return True
            else:
                logger.warning(f"Image {filename} not found for deletion")
                return False

        except IOError as e:
            logger.error(f"Failed to delete image {filename}: {e}")
            return False
