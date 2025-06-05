"""
Configuration settings for Google Books API.
Uses enum values to ensure consistency across the application.
"""

from enums.book_fields import BookField, BookDefaultFields

# Google Books API endpoint
GOOGLE_BOOKS_API_BASE_URL = "https://www.googleapis.com/books/v1/volumes"

# Default set of fields to retrieve when not specified
DEFAULT_FIELDS = BookDefaultFields.DEFAULT_FIELDS

# Mandatory fields that will always be included in responses
MANDATORY_FIELDS = BookDefaultFields.MANDATORY_FIELDS

# Field mappings between Google Books API response and our standardized format
FIELD_MAPPINGS = {
    BookField.ISBN.value: "industryIdentifiers",  # Special handling required for ISBN
    BookField.TITLE.value: "title",
    BookField.AUTHORS.value: "authors",
    BookField.PUBLISHER.value: "publisher",
    BookField.PUBLISHED_DATE.value: "publishedDate",
    BookField.DESCRIPTION.value: "description",
    BookField.PAGE_COUNT.value: "pageCount",
    BookField.CATEGORIES.value: "categories",
    BookField.IMAGE_LINKS.value: "imageLinks",
    BookField.LANGUAGE.value: "language",
    BookField.ID.value: "id",
    BookField.MATURITY_RATING.value: "maturityRating",
    BookField.AVERAGE_RATING.value: "averageRating",
    BookField.RATINGS_COUNT.value: "ratingsCount"
}
