from typing import Dict, Any
from models.content_model import ContentModel
from config.content_config import DEFAULT_WORKFLOW_STATUS, VALID_WORKFLOW_STATUSES


class AudioContent(ContentModel):
    """
    Audio-specific content model with attributes specific to audio content.
    """
    
    def __init__(self, content_data: Dict):
        super().__init__(
            content_data.get("content_id"),
            content_data.get("user_id"),
            content_data.get("insert_time")
        )
        # TODO: Add audio-specific attributes as specified by the user
        self.title: str = content_data.get("title", "")
        self.duration: int = content_data.get("duration", 0)  # Duration in seconds
        self.format: str = content_data.get("format", "")  # e.g., mp3, wav
        self.rag_status: str = content_data.get("rag_status", DEFAULT_WORKFLOW_STATUS)
        self.training_status: str = content_data.get("training_status", DEFAULT_WORKFLOW_STATUS)
        self.licensing_status: str = content_data.get("licensing_status", DEFAULT_WORKFLOW_STATUS)
        
        # Validate status values
        self._validate_statuses()
    
    def _validate_statuses(self):
        """Validate that all status fields have valid values."""
        status_fields = {
            "rag_status": self.rag_status,
            "training_status": self.training_status,
            "licensing_status": self.licensing_status
        }
        
        for field_name, value in status_fields.items():
            if value not in VALID_WORKFLOW_STATUSES:
                raise ValueError(f"Invalid {field_name}: {value}. Valid values: {', '.join(VALID_WORKFLOW_STATUSES)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary representation."""
        return {
            "content_id": self.content_id,
            "user_id": self.user_id,
            "insert_time": self.insert_time,
            "type": "AUDIO",
            "title": self.title,
            "duration": self.duration,
            "format": self.format,
            "rag_status": self.rag_status,
            "training_status": self.training_status,
            "licensing_status": self.licensing_status
        }
