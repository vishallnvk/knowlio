"""
Enum definitions for book fields and constants.
Provides standardized, type-safe constants for book attributes.
"""

from enum import Enum


class BookField(Enum):
    """
    Enum representing the standard fields used in book metadata.
    Used for consistent field naming and validation.
    """
    TITLE = "title"
    AUTHORS = "authors"
    PUBLISHER = "publisher"
    PUBLISHED_DATE = "publishedDate"
    DESCRIPTION = "description"
    ISBN = "isbn"
    PAGE_COUNT = "pageCount"
    CATEGORIES = "categories"
    LANGUAGE = "language"
    IMAGE_LINKS = "imageLinks"
    ID = "id"
    MATURITY_RATING = "maturityRating"
    AVERAGE_RATING = "averageRating"
    RATINGS_COUNT = "ratingsCount"

    @classmethod
    def get_all_fields(cls) -> list:
        """Get a list of all field names as strings"""
        return [field.value for field in cls]

    @classmethod
    def is_valid(cls, field: str) -> bool:
        """Check if a string value is a valid book field"""
        return field in cls.get_all_fields()


class BookImageLink(Enum):
    """
    Enum representing the standard image link types available from Google Books API.
    Used for consistent access to different image formats.
    """
    THUMBNAIL = "thumbnail"
    SMALL_THUMBNAIL = "smallThumbnail"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    EXTRA_LARGE = "extraLarge"

    @classmethod
    def get_all_types(cls) -> list:
        """Get a list of all image link types as strings"""
        return [link_type.value for link_type in cls]


class BookDataSource(Enum):
    """
    Enum representing the possible sources of book data.
    Used to track the provenance of book information.
    """
    GOOGLE_BOOKS = "google_books"
    USER_INPUT = "user_input"
    OPEN_LIBRARY = "open_library"
    MANUAL = "manual"


class BookDefaultFields:
    """
    Class holding default field selections for book APIs.
    Used for consistent default field selection across the application.
    """
    DEFAULT_FIELDS = [
        BookField.TITLE.value,
        BookField.AUTHORS.value, 
        BookField.ISBN.value,
        BookField.PUBLISHER.value,
        BookField.PUBLISHED_DATE.value
    ]
    
    MANDATORY_FIELDS = [
        BookField.TITLE.value,
        BookField.AUTHORS.value,
        BookField.ISBN.value
    ]
