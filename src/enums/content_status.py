"""
Enum definitions for content status values.
Provides standardized, type-safe constants for content lifecycle and workflow statuses.
"""

from enum import Enum, auto


class ContentStatus(Enum):
    """
    Enum representing the lifecycle status of content items.
    Used to track content through its lifecycle from creation to archival.
    """
    DRAFT = "DRAFT"      # Initial draft state, not fully published
    ACTIVE = "ACTIVE"    # Published and available content
    ARCHIVED = "ARCHIVED"  # No longer actively available, but preserved

    @classmethod
    def get_valid_statuses(cls) -> list:
        """Get a list of all valid status values as strings"""
        return [status.value for status in cls]

    @classmethod
    def is_valid(cls, status: str) -> bool:
        """Check if a string value is a valid content status"""
        return status in cls.get_valid_statuses()


class WorkflowStatus(Enum):
    """
    Enum representing workflow processing status for content items.
    Used for various processing pipelines like RAG, training, licensing.
    """
    ENABLED = "ENABLED"   # Processing is enabled for this content
    DISABLED = "DISABLED"  # Processing is disabled for this content

    @classmethod
    def get_valid_statuses(cls) -> list:
        """Get a list of all valid workflow status values as strings"""
        return [status.value for status in cls]

    @classmethod
    def is_valid(cls, status: str) -> bool:
        """Check if a string value is a valid workflow status"""
        return status in cls.get_valid_statuses()
