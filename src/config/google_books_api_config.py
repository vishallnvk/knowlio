"""
Configuration settings for Google Books API.
"""

# Google Books API endpoint
GOOGLE_BOOKS_API_BASE_URL = "https://www.googleapis.com/books/v1/volumes"

# Default set of fields to retrieve when not specified
DEFAULT_FIELDS = [
    "isbn",
    "title",
    "authors",
    "publisher",
    "publishedDate",
    "description",
    "pageCount",
    "categories",
    "imageLinks",
    "language"
]

# Mandatory fields that will always be included in responses
MANDATORY_FIELDS = [
    "isbn",
    "title",
    "authors"
]

# Field mappings between Google Books API response and our standardized format
FIELD_MAPPINGS = {
    "isbn": "industryIdentifiers",  # Special handling required for ISBN
    "title": "title",
    "authors": "authors",
    "publisher": "publisher",
    "publishedDate": "publishedDate",
    "description": "description",
    "pageCount": "pageCount",
    "categories": "categories",
    "imageLinks": "imageLinks",
    "language": "language"
}
