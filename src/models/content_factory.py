from typing import Dict, List
from models.content_model import ContentModel
from models.book_content import BookContent
from models.audio_content import AudioContent
from config.content_config import CONTENT_TYPES


class ContentFactory:
    """
    Factory class to create appropriate content type instances based on the type parameter.
    """
    
    @staticmethod
    def create_content(content_type: str, content_data: Dict) -> ContentModel:
        """
        Create and return the appropriate content type instance.
        
        Args:
            content_type: The type of content (BOOK, AUDIO, etc.)
            content_data: Dictionary containing the content data
            
        Returns:
            Instance of the appropriate content type
            
        Raises:
            ValueError: If the content type is unknown
        """
        content_type_upper = content_type.upper()
        
        if content_type_upper == CONTENT_TYPES["BOOK"]:
            return BookContent(content_data)
        elif content_type_upper == CONTENT_TYPES["AUDIO"]:
            return AudioContent(content_data)
        # Add more content types as needed
        else:
            raise ValueError(f"Unknown content type: {content_type}")
    
    @staticmethod
    def get_supported_types() -> List[str]:
        """Return a list of supported content types."""
        return list(CONTENT_TYPES.values())
