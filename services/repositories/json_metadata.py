"""JSON file implementation for metadata storage."""

import json
import logging
from pathlib import Path
from filelock import FileLock

from .base import MetadataRepository

logger = logging.getLogger(__name__)


class JsonMetadataRepository(MetadataRepository):
    """Store image metadata in a JSON file."""

    def __init__(self, json_path: Path):
        """
        Initialize JSON metadata storage.

        Args:
            json_path: Path to the JSON file storing metadata
        """
        self.json_path = Path(json_path)
        self.lock_path = self.json_path.with_suffix(".json.lock")

        # Ensure the file exists with valid structure
        if not self.json_path.exists():
            with FileLock(self.lock_path):
                self._write_data_unlocked({"images": []})

    def _read_data(self) -> dict:
        """Read and parse the JSON file. Caller must hold lock if needed."""
        try:
            with open(self.json_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read metadata file: {e}")
            return {"images": []}

    def _write_data_unlocked(self, data: dict) -> bool:
        """Write data to JSON file. Caller must hold lock."""
        try:
            with open(self.json_path, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except IOError as e:
            logger.error(f"Failed to write metadata file: {e}")
            return False

    def save_metadata(self, image_data: dict) -> bool:
        """Save or update metadata for an image."""
        with FileLock(self.lock_path):
            data = self._read_data()
            images = data.get("images", [])

            # Check if image with this ID already exists
            existing_idx = None
            for idx, img in enumerate(images):
                if img.get("id") == image_data.get("id"):
                    existing_idx = idx
                    break

            if existing_idx is not None:
                # Update existing entry
                images[existing_idx] = image_data
                logger.info(f"Updated metadata for image {image_data.get('id')}")
            else:
                # Add new entry
                images.append(image_data)
                logger.info(f"Added metadata for image {image_data.get('id')}")

            data["images"] = images
            return self._write_data_unlocked(data)

    def get_all_metadata(self) -> list[dict]:
        """Retrieve all image metadata."""
        data = self._read_data()
        return data.get("images", [])

    def get_metadata_by_id(self, image_id: str) -> dict | None:
        """Retrieve metadata for a specific image."""
        data = self._read_data()
        for img in data.get("images", []):
            if img.get("id") == image_id:
                return img
        return None

    def delete_metadata(self, image_id: str) -> bool:
        """Delete metadata for an image."""
        with FileLock(self.lock_path):
            data = self._read_data()
            images = data.get("images", [])

            original_len = len(images)
            images = [img for img in images if img.get("id") != image_id]

            if len(images) < original_len:
                data["images"] = images
                logger.info(f"Deleted metadata for image {image_id}")
                return self._write_data_unlocked(data)
            else:
                logger.warning(f"Image {image_id} not found for deletion")
                return False
