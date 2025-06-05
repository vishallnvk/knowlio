from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid

from enums.content_type import ContentType
from enums.content_status import ContentStatus, WorkflowStatus


class ContentModel:
    """
    Flexible content model that can represent various types of content (books, videos, datasets, etc.)
    
    Core attributes are stored as direct properties, while type-specific attributes
    are stored in the metadata dictionary.
    
    Status fields can be flexibly updated to support various workflows (RAG, training, licensing, etc.)
    """
    
    # Valid content types - Use enum values
    VALID_TYPES = ContentType.get_valid_types()
    
    # Valid status values - Use enum values
    VALID_STATUSES = ContentStatus.get_valid_statuses()
    
    # Valid workflow status values - Use enum values
    VALID_WORKFLOW_STATUSES = WorkflowStatus.get_valid_statuses()
    
    def __init__(self, content_data: Dict):
        # Core properties
        self.content_id: str = content_data.get("content_id", str(uuid.uuid4()))
        self.publisher_id: str = content_data["publisher_id"]
        self.title: str = content_data["title"]
        self.type: str = self._validate_type(content_data["type"])
        self.tags: List[str] = content_data.get("tags", [])
        self.description: str = content_data.get("description", "")
        
        # Flexible metadata for type-specific attributes
        self.metadata: Dict = content_data.get("metadata", {})
        
        # Core status
        self.status: str = content_data.get("status", ContentStatus.DRAFT.value)
        
        # File storage
        self.file_key: Optional[str] = content_data.get("file_key")
        
        # Timestamps
        self.created_at: str = content_data.get("created_at", datetime.utcnow().isoformat())
        self.updated_at: Optional[str] = content_data.get("updated_at")
        
        # Workflow statuses - initialize with default values if not provided
        self.rag_status: str = content_data.get("rag_status", WorkflowStatus.DISABLED.value)
        self.training_status: str = content_data.get("training_status", WorkflowStatus.DISABLED.value)
        self.licensing_status: str = content_data.get("licensing_status", WorkflowStatus.DISABLED.value)
        
    def _validate_type(self, content_type: str) -> str:
        """Validate and normalize content type"""
        normalized_type = content_type.upper()
        if not ContentType.is_valid(normalized_type):
            raise ValueError(f"Invalid content type: {content_type}. Valid types: {', '.join(ContentType.get_valid_types())}")
        return normalized_type
    
    @classmethod
    def validate_status(cls, status: str) -> bool:
        """Validate content status value"""
        return ContentStatus.is_valid(status)
    
    @classmethod
    def validate_workflow_status(cls, status: str) -> bool:
        """Validate workflow status value"""
        return WorkflowStatus.is_valid(status)
