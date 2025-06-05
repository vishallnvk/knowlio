"""
Helper class for interacting with the Google Books API.
Provides methods to fetch and filter book details by ISBN.
"""

import urllib.request
import urllib.error
import urllib.parse
import json
import time
from typing import Dict, List, Optional, Any

from helpers.common_helper.logger_helper import LoggerHelper
from helpers.common_helper.common_helper import Retry
from models.book_model import BookModel
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

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[urllib.error.URLError, json.JSONDecodeError])
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
            
            # Use the BookModel to process and return the full book data
            book = BookModel({
                'volumeInfo': volume_info,
                'isbn': isbn,
                'id': data['items'][0].get('id')
            })
            return book.to_dict()
            
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

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[urllib.error.URLError, json.JSONDecodeError])
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
        
        # Create a BookModel and use its filtering method
        book_model = BookModel(book_data)
        filtered_data = book_model.filter_fields(fields_to_include)
        
        logger.debug(f"Filtered book data to fields: {list(filtered_data.keys())}")
        return filtered_data

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[urllib.error.URLError, json.JSONDecodeError])
    def get_books_by_author_filtered(self, author_name: str, fields: Optional[List[str]] = None, max_results: int = 100) -> Dict[str, Any]:
        """
        Fetch all books by a specific author with only specified fields.
        
        Args:
            author_name: The name of the author to search for
            fields: List of fields to include in the response (in addition to mandatory fields)
            max_results: Maximum number of results to return (default: 100)
            
        Returns:
            Dict containing a list of filtered books and metadata
        """
        # First get all books by the author
        result = self.get_books_by_author(author_name, max_results)
        
        # If there was an error or no books found, return the result as is
        if "error" in result or not result.get("books"):
            return result
        
        # If fields not specified, use defaults
        if fields is None:
            fields = DEFAULT_FIELDS
        
        # Ensure mandatory fields are always included
        fields_to_include = set(fields).union(set(MANDATORY_FIELDS))
        
        # Filter each book to include only the requested fields
        filtered_books = []
        for book in result["books"]:
            # Create a BookModel and use its filtering method
            book_model = BookModel(book)
            filtered_book = book_model.filter_fields(fields_to_include)
            filtered_books.append(filtered_book)
        
        # Return the result with filtered books
        result["books"] = filtered_books
        return result

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[urllib.error.URLError, json.JSONDecodeError])
    def get_books_by_author(self, author_name: str, max_results: int = 100) -> Dict[str, Any]:
        """
        Fetch all books by a specific author from Google Books API.
        Handles pagination to return a complete list up to max_results.
        
        Args:
            author_name: The name of the author to search for
            max_results: Maximum number of results to return (default: 100)
            
        Returns:
            Dict containing a list of books and metadata
        """
        logger.info(f"Fetching books by author: {author_name}")
        
        # URL encode the author name
        author_query = urllib.parse.quote(f'inauthor:"{author_name}"')
        base_url = f"{self.api_base_url}?q={author_query}&orderBy=relevance"
        
        all_books = []
        start_index = 0
        items_per_page = min(40, max_results)  # Google Books API maximum is 40 per page
        
        try:
            # Loop through pages until we have all results or hit max_results
            while len(all_books) < max_results:
                # Construct URL with pagination parameters
                url = f"{base_url}&startIndex={start_index}&maxResults={items_per_page}"
                logger.debug(f"Fetching page with startIndex={start_index}")
                
                # Make the request
                with urllib.request.urlopen(url) as response:
                    response_data = response.read().decode('utf-8')
                    data = json.loads(response_data)
                
                # Check if we have any items
                total_items = data.get('totalItems', 0)
                if total_items == 0:
                    if start_index == 0:
                        logger.warning(f"No books found for author: {author_name}")
                        return {"books": [], "total_found": 0, "author": author_name}
                    break
                    
                # Process items on this page
                items = data.get('items', [])
                if not items:
                    break
                    
                # Process each book and add to our results
                for item in items:
                    volume_info = item.get('volumeInfo', {})
                    # Only include if the author exactly matches (the API sometimes returns partial matches)
                    item_authors = volume_info.get('authors', [])
                    if any(author_name.lower() in author.lower() for author in item_authors):
                        # Extract ISBN if available
                        isbn = None
                        industry_ids = volume_info.get('industryIdentifiers', [])
                        for id_item in industry_ids:
                            if id_item.get('type') == 'ISBN_13':
                                isbn = id_item.get('identifier')
                                break
                            elif id_item.get('type') == 'ISBN_10':
                                isbn = id_item.get('identifier')
                        
                        # Create a book model and add its dictionary representation to results
                        book_model = BookModel({
                            'volumeInfo': volume_info,
                            'isbn': isbn,
                            'id': item.get('id')
                        })
                        
                        all_books.append(book_model.to_dict())
                
                # Update for next page
                start_index += len(items)
                
                # If we got fewer items than requested, we've reached the end
                if len(items) < items_per_page:
                    break
                    
                # If we have enough results, stop
                if len(all_books) >= max_results:
                    all_books = all_books[:max_results]  # Trim to max_results
                    break
                    
                # To avoid overwhelming the API, add a small delay between requests
                # In production, you might want to implement a more sophisticated rate limiter
                time.sleep(0.2)
            
            logger.info(f"Found {len(all_books)} books by author: {author_name}")
            return {
                "books": all_books,
                "total_found": len(all_books),
                "author": author_name,
                "truncated": len(all_books) >= max_results  # Indicates if results were truncated
            }
            
        except urllib.error.URLError as e:
            logger.error(f"API request error: {str(e)}")
            return {"error": f"Failed to fetch books: {str(e)}"}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse API response: {str(e)}")
            return {"error": "Invalid JSON response from Google Books API"}
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {"error": f"An unexpected error occurred: {str(e)}"}
