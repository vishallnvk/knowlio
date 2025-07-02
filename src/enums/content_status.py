from enum import Enum


class ContentStatus(Enum):
    """
    Enum for content status values.
    """
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    
    @classmethod
    def get_valid_statuses(cls):
        """Get all valid status values"""
        return [status.value for status in cls]
    
    @classmethod
    def is_valid(cls, status: str) -> bool:
        """Check if a status value is valid"""
        return status in cls.get_valid_statuses()


class WorkflowStatus(Enum):
    """
    Enum for workflow status values.
    Changed to use ENABLED/DISABLED as per requirements.
    """
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    
    # Define which fields use workflow status
    WORKFLOW_STATUS_FIELDS = ["rag_status", "training_status", "licensing_status"]
    
    @classmethod
    def get_valid_statuses(cls):
        """Get all valid workflow status values"""
        return [status.value for status in cls]
    
    @classmethod
    def is_valid(cls, status: str) -> bool:
        """Check if a workflow status value is valid"""
        return status in cls.get_valid_statuses()
