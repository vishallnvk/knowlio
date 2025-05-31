from datetime import datetime
from typing import Dict, List, Optional
import uuid


class ContentModel:
    def __init__(self, content_data: Dict):
        self.content_id: str = str(uuid.uuid4())
        self.publisher_id: str = content_data["publisher_id"]
        self.title: str = content_data["title"]
        self.type: str = content_data["type"]  # e.g., book, video, dataset
        self.tags: List[str] = content_data.get("tags", [])
        self.description: str = content_data.get("description", "")
        self.metadata: Dict = content_data.get("metadata", {})
        self.status: str = "DRAFT"
        self.file_key: Optional[str] = None
        self.created_at: str = datetime.utcnow().isoformat()