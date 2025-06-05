"""
Model for representing a book retrieved from Google Books API.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from enums.book_fields import BookField, BookDefaultFields, BookDataSource


class BookModel:
    """
    Model representing a book from Google Books API with all its details.
    """
    def __init__(self, book_data: Dict[str, Any], source: str = BookDataSource.GOOGLE_BOOKS.value):
        """
        Initialize a book model from book data.
        
        Args:
            book_data: Dictionary containing book details that may include:
                - volumeInfo: The volumeInfo section from the Google Books API
                - isbn: Optional ISBN if known from request context
                - id: Optional Google Books ID
            source: Source of the book data (default: GOOGLE_BOOKS)
        """
        volume_info = book_data.get('volumeInfo', book_data)
        
        # Core book properties
        self.title: str = volume_info.get(BookField.TITLE.value, 'Unknown Title')
        self.authors: List[str] = volume_info.get(BookField.AUTHORS.value, ['Unknown Author'])
        self.publisher: Optional[str] = volume_info.get(BookField.PUBLISHER.value)
        self.published_date: Optional[str] = volume_info.get(BookField.PUBLISHED_DATE.value)
        self.description: Optional[str] = volume_info.get(BookField.DESCRIPTION.value)
        self.page_count: Optional[int] = volume_info.get(BookField.PAGE_COUNT.value)
        self.categories: List[str] = volume_info.get(BookField.CATEGORIES.value, [])
        self.language: Optional[str] = volume_info.get(BookField.LANGUAGE.value)
        
        # Image links
        self.image_links: Dict[str, str] = volume_info.get(BookField.IMAGE_LINKS.value, {})
        
        # Identifier properties
        self.id: Optional[str] = book_data.get(BookField.ID.value)
        self.isbn: Optional[str] = self._extract_isbn(volume_info, book_data.get(BookField.ISBN.value))
        
        # Additional metadata
        self.maturity_rating: Optional[str] = volume_info.get(BookField.MATURITY_RATING.value)
        self.average_rating: Optional[float] = volume_info.get(BookField.AVERAGE_RATING.value)
        self.ratings_count: Optional[int] = volume_info.get(BookField.RATINGS_COUNT.value)
        
        # Source tracking
        self.source: str = source
        
    def _extract_isbn(self, volume_info: Dict[str, Any], default_isbn: Optional[str] = None) -> Optional[str]:
        """
        Extract ISBN from industry identifiers or use provided default.
        
        Args:
            volume_info: The volumeInfo section from Google Books API
            default_isbn: Default ISBN to use if none found in volume_info
            
        Returns:
            ISBN as string or None if not available
        """
        # Try to extract from industry identifiers
        industry_ids = volume_info.get('industryIdentifiers', [])
        
        # Prefer ISBN-13 over ISBN-10
        for id_item in industry_ids:
            if id_item.get('type') == 'ISBN_13':
                return id_item.get('identifier')
                
        # Fall back to ISBN-10 if ISBN-13 not found
        for id_item in industry_ids:
            if id_item.get('type') == 'ISBN_10':
                return id_item.get('identifier')
                
        # Return default if provided, otherwise None
        return default_isbn
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the book model to a dictionary representation.
        
        Returns:
            Dictionary containing all book properties
        """
        return {
            BookField.TITLE.value: self.title,
            BookField.AUTHORS.value: self.authors,
            BookField.PUBLISHER.value: self.publisher,
            BookField.PUBLISHED_DATE.value: self.published_date,
            BookField.DESCRIPTION.value: self.description,
            BookField.PAGE_COUNT.value: self.page_count,
            BookField.CATEGORIES.value: self.categories,
            BookField.LANGUAGE.value: self.language,
            BookField.IMAGE_LINKS.value: self.image_links,
            BookField.ID.value: self.id,
            BookField.ISBN.value: self.isbn,
            BookField.MATURITY_RATING.value: self.maturity_rating,
            BookField.AVERAGE_RATING.value: self.average_rating,
            BookField.RATINGS_COUNT.value: self.ratings_count,
            "source": self.source  # Not part of BookField as it's metadata about the record
        }
        
    def filter_fields(self, fields: List[str], mandatory_fields: List[str] = BookDefaultFields.MANDATORY_FIELDS) -> Dict[str, Any]:
        """
        Filter the book data to include only specified fields.
        
        Args:
            fields: List of fields to include
            mandatory_fields: List of fields that must always be included
            
        Returns:
            Dictionary containing only the specified fields
        """
        all_book_data = self.to_dict()
        
        # Determine fields to include
        fields_to_include = set(fields)
        if mandatory_fields:
            fields_to_include = fields_to_include.union(set(mandatory_fields))
            
        # Filter the dictionary
        filtered_data = {
            field: all_book_data.get(field) 
            for field in fields_to_include 
            if field in all_book_data
        }
        
        return filtered_data
