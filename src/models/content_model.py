from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid


class ContentModel:
    """
    Base content model with common attributes for all content types.
    All content types will inherit from this base class.
    """
    
    def __init__(self, content_id: str = None, user_id: str = None, insert_time: str = None, content_type: str = None):
        self.content_id: str = content_id or str(uuid.uuid4())
        self.user_id: str = user_id
        self.insert_time: str = insert_time or datetime.utcnow().isoformat()
        self.content_type: str = content_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary representation."""
        base_dict = {
            "content_id": self.content_id,
            "user_id": self.user_id,
            "insert_time": self.insert_time
        }
        
        # Add composite key for user-aware pagination (fixes pagination bug)
        # Format: user_id#type (e.g., "user123#BOOK")
        if self.user_id and self.content_type:
            base_dict["user_type_key"] = f"{self.user_id}#{self.content_type}"
        
        return base_dict
