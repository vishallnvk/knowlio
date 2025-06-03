"""
Helper class for interacting with the Google Books API.
Provides methods to fetch and filter book details by ISBN.
"""

import urllib.request
import urllib.error
import json
from typing import Dict, List, Optional, Any

from helpers.common_helper.logger_helper import LoggerHelper
from config.google_books_api_config import (
    GOOGLE_BOOKS_API_BASE_URL,
    DEFAULT_FIELDS,
    MANDATORY_FIELDS,
    FIELD_MAPPINGS
)

logger = LoggerHelper(__name__).get_logger()

class GoogleBooksHelper:
    def __init__(self):
        self.api_base_url = GOOGLE_BOOKS_API_BASE_URL

    def get_book_details(self, isbn: str) -> Dict[str, Any]:
        """
        Fetch book details from Google Books API using ISBN.
        
        Args:
            isbn: The ISBN of the book to look up
            
        Returns:
            Dict containing book details
        """
        logger.info(f"Fetching book details for ISBN: {isbn}")
        
        url = f"{self.api_base_url}?q=isbn:{isbn}"
        
        try:
            # Use urllib instead of requests
            with urllib.request.urlopen(url) as response:
                response_data = response.read().decode('utf-8')
                data = json.loads(response_data)
            
            if data.get('totalItems', 0) == 0:
                logger.warning(f"No books found for ISBN: {isbn}")
                return {"error": f"No book found with ISBN {isbn}"}
                
            # Extract the first volume item (most relevant match)
            volume_info = data['items'][0]['volumeInfo']
            logger.debug(f"Found book: {volume_info.get('title', 'Unknown')}")
            
            # Process and return the full book data
            return self._process_book_data(volume_info, isbn)
            
        except urllib.error.URLError as e:
            logger.error(f"API request error: {str(e)}")
            return {"error": f"Failed to fetch book data: {str(e)}"}
        except KeyError as e:
            logger.error(f"Unexpected response format: {str(e)}")
            return {"error": "Invalid response format from Google Books API"}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse API response: {str(e)}")
            return {"error": "Invalid JSON response from Google Books API"}
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {"error": f"An unexpected error occurred: {str(e)}"}

    def get_book_details_filtered(self, isbn: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Fetch book details with only specified fields plus mandatory fields.
        
        Args:
            isbn: The ISBN of the book to look up
            fields: List of fields to include in the response (in addition to mandatory fields)
            
        Returns:
            Dict containing the filtered book details
        """
        # Get all book details first
        book_data = self.get_book_details(isbn)
        
        # If an error occurred, return it directly
        if "error" in book_data:
            return book_data
        
        # If fields not specified, use defaults
        if fields is None:
            fields = DEFAULT_FIELDS
        
        # Ensure mandatory fields are always included
        fields_to_include = set(fields).union(set(MANDATORY_FIELDS))
        
        # Filter the book data to only include requested fields
        filtered_data = {
            field: book_data.get(field) 
            for field in fields_to_include 
            if field in book_data
        }
        
        logger.debug(f"Filtered book data to fields: {list(filtered_data.keys())}")
        return filtered_data

    def _process_book_data(self, volume_info: Dict[str, Any], isbn: str) -> Dict[str, Any]:
        """
        Process the Google Books API response to extract and normalize book data.
        
        Args:
            volume_info: The volumeInfo section from the Google Books API response
            isbn: The ISBN used in the original query
            
        Returns:
            Dict containing the processed book data
        """
        processed_data = {}
        
        # Process each field according to mappings
        for our_field, google_field in FIELD_MAPPINGS.items():
            # Handle ISBN specially
            if our_field == "isbn":
                # Extract ISBN from industry identifiers
                industry_ids = volume_info.get('industryIdentifiers', [])
                # Try to find ISBN-13 first, then ISBN-10
                isbn_value = isbn  # Default to the provided ISBN
                for id_item in industry_ids:
                    if id_item.get('type') == 'ISBN_13':
                        isbn_value = id_item.get('identifier')
                        break
                    elif id_item.get('type') == 'ISBN_10':
                        isbn_value = id_item.get('identifier')
                processed_data[our_field] = isbn_value
            else:
                # For all other fields, directly map from Google's response
                processed_data[our_field] = volume_info.get(google_field)
                
        # Add any additional processing or formatting here if needed
        
        return processed_data
