"""Abstract base classes for storage repositories."""

from abc import ABC, abstractmethod
from typing import BinaryIO


class ImageStorageRepository(ABC):
    """Abstract interface for image storage operations."""

    @abstractmethod
    def save_image(self, file: BinaryIO, filename: str) -> str:
        """
        Save an image file to storage.

        Args:
            file: File-like object containing image data
            filename: Target filename for the image

        Returns:
            URL or path to access the saved image
        """
        pass

    @abstractmethod
    def get_image_url(self, filename: str) -> str:
        """
        Get the URL for accessing an image.

        Args:
            filename: The filename of the stored image

        Returns:
            URL to access the image
        """
        pass

    @abstractmethod
    def delete_image(self, filename: str) -> bool:
        """
        Delete an image from storage.

        Args:
            filename: The filename of the image to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        pass


class MetadataRepository(ABC):
    """Abstract interface for image metadata storage operations."""

    @abstractmethod
    def save_metadata(self, image_data: dict) -> bool:
        """
        Save or update metadata for an image.

        Args:
            image_data: Dictionary containing image metadata
                       (id, filename, description, tags)

        Returns:
            True if saved successfully, False otherwise
        """
        pass

    @abstractmethod
    def get_all_metadata(self) -> list[dict]:
        """
        Retrieve all image metadata.

        Returns:
            List of dictionaries containing image metadata
        """
        pass

    @abstractmethod
    def get_metadata_by_id(self, image_id: str) -> dict | None:
        """
        Retrieve metadata for a specific image.

        Args:
            image_id: The unique identifier for the image

        Returns:
            Dictionary containing image metadata, or None if not found
        """
        pass

    @abstractmethod
    def delete_metadata(self, image_id: str) -> bool:
        """
        Delete metadata for an image.

        Args:
            image_id: The unique identifier for the image

        Returns:
            True if deleted successfully, False otherwise
        """
        pass
