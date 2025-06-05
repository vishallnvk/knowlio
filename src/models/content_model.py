from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid


class ContentModel:
    """
    Flexible content model that can represent various types of content (books, videos, datasets, etc.)
    
    Core attributes are stored as direct properties, while type-specific attributes
    are stored in the metadata dictionary.
    
    Status fields can be flexibly updated to support various workflows (RAG, training, licensing, etc.)
    """
    
    # Valid content types
    VALID_TYPES = ["BOOK", "VIDEO", "AUDIO", "DATASET", "TEXT"]
    
    # Valid status values
    VALID_STATUSES = ["DRAFT", "ACTIVE", "ARCHIVED"]
    
    # Valid workflow status values
    VALID_WORKFLOW_STATUSES = ["ENABLED", "DISABLED"]
    
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
        self.status: str = content_data.get("status", "DRAFT")
        
        # File storage
        self.file_key: Optional[str] = content_data.get("file_key")
        
        # Timestamps
        self.created_at: str = content_data.get("created_at", datetime.utcnow().isoformat())
        self.updated_at: Optional[str] = content_data.get("updated_at")
        
        # Workflow statuses - initialize with default values if not provided
        self.rag_status: str = content_data.get("rag_status", "DISABLED")
        self.training_status: str = content_data.get("training_status", "DISABLED")
        self.licensing_status: str = content_data.get("licensing_status", "DISABLED")
        
    def _validate_type(self, content_type: str) -> str:
        """Validate and normalize content type"""
        normalized_type = content_type.upper()
        if normalized_type not in self.VALID_TYPES:
            raise ValueError(f"Invalid content type: {content_type}. Valid types: {', '.join(self.VALID_TYPES)}")
        return normalized_type
    
    @classmethod
    def validate_status(cls, status: str) -> bool:
        """Validate content status value"""
        return status in cls.VALID_STATUSES
    
    @classmethod
    def validate_workflow_status(cls, status: str) -> bool:
        """Validate workflow status value"""
        return status in cls.VALID_WORKFLOW_STATUSES
