from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid


class ContentModel:
    """
    Base content model with only content_id as the common attribute.
    All content types will inherit from this base class.
    """
    
    def __init__(self, content_id: str = None):
        self.content_id: str = content_id or str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary representation."""
        return {
            "content_id": self.content_id
        }
