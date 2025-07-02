from typing import Dict, List, Any
from models.content_model import ContentModel
from config.content_config import DEFAULT_WORKFLOW_STATUS, VALID_WORKFLOW_STATUSES


class BookContent(ContentModel):
    """
    Book-specific content model with attributes specific to books.
    """
    
    def __init__(self, content_data: Dict):
        super().__init__(content_data.get("content_id"))
        self.authors: List[str] = content_data.get("authors", [])
        self.publisher: str = content_data.get("publisher", "")
        self.year: str = content_data.get("year", "")
        self.isbn: str = content_data.get("isbn", "")
        self.title: str = content_data.get("title", "")
        self.keywords: List[str] = content_data.get("keywords", [])
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
            "type": "BOOK",
            "authors": self.authors,
            "publisher": self.publisher,
            "year": self.year,
            "isbn": self.isbn,
            "title": self.title,
            "keywords": self.keywords,
            "rag_status": self.rag_status,
            "training_status": self.training_status,
            "licensing_status": self.licensing_status
        }
