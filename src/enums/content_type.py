"""
Enum definitions for content types.
Provides standardized, type-safe constants for different content media types.
"""

from enum import Enum


class ContentType(Enum):
    """
    Enum representing the different types of content that can be managed.
    Used to classify content by its media type and format.
    """
    BOOK = "BOOK"       # Book content type (PDF, EPUB, etc.)
    VIDEO = "VIDEO"     # Video content type (MP4, etc.)
    AUDIO = "AUDIO"     # Audio content type (MP3, etc.)
    DATASET = "DATASET"  # Dataset content type (CSV, JSON, etc.)
    TEXT = "TEXT"       # Plain text content type

    @classmethod
    def get_valid_types(cls) -> list:
        """Get a list of all valid content types as strings"""
        return [content_type.value for content_type in cls]

    @classmethod
    def is_valid(cls, content_type: str) -> bool:
        """Check if a string value is a valid content type"""
        return content_type in cls.get_valid_types()
