"""
Processor for Google Books API operations.
Provides actions to fetch and filter book details by ISBN.
"""

from typing import Dict, List, Optional, Any

from helpers.common_helper.common_helper import require_keys
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.common_helper.auth_helper import require_role, get_authenticated_user_id
from helpers.common_helper.auth_context import AuthContext
from helpers.app_logic_helpers.google_books_helper import GoogleBooksHelper
from sync_processor_registry.processor_registry import ProcessorRegistry
from sync_processors.base_processor import BaseProcessor
from enums.book_fields import BookField, BookDefaultFields

logger = LoggerHelper(__name__).get_logger()


@ProcessorRegistry.register("google_books")
class GoogleBooksProcessor(BaseProcessor):
    def __init__(self):
        self.helper = GoogleBooksHelper()
        super().__init__({
            "get_book_details": self._get_book_details,
            "get_book_details_filtered": self._get_book_details_filtered,
            "get_books_by_author": self._get_books_by_author,
            "get_books_by_author_filtered": self._get_books_by_author_filtered,
        })

    def _get_book_details(self, payload: Dict) -> Dict:
        """
        Get complete book details from Google Books API by ISBN.
        
        Args:
            payload: Dict containing 'isbn' key
            
        Returns:
            Dict containing book details or error message
        """
        try:
            require_keys(payload, ["isbn"])
            
            # Log who is making the request
            auth_context = AuthContext.from_payload(payload)
            if auth_context.is_authenticated():
                logger.info(f"User {auth_context.user_id} ({auth_context.role}) fetching book details for ISBN: {payload['isbn']}")
                
            return self.helper.get_book_details(payload["isbn"])
        except Exception as e:
            logger.error(f"Error fetching book details: {str(e)}")
            return {"error": f"Failed to fetch book details: {str(e)}"}

    def _get_book_details_filtered(self, payload: Dict) -> Dict:
        """
        Get filtered book details from Google Books API by ISBN.
        
        Args:
            payload: Dict containing 'isbn' key and optional 'fields' list
            
        Returns:
            Dict containing filtered book details or error message
        """
        try:
            require_keys(payload, ["isbn"])
            fields = payload.get("fields", BookDefaultFields.DEFAULT_FIELDS)
            
            # Log who is making the request
            user_id = get_authenticated_user_id(payload)
            if user_id:
                logger.info(f"User {user_id} fetching filtered book details for ISBN: {payload['isbn']}")
            
            # If fields is provided, ensure it's a list
            if not isinstance(fields, list):
                logger.error("Invalid 'fields' parameter: must be a list")
                return {"error": "Invalid 'fields' parameter: must be a list of field names"}
            
            # Validate field names if provided
            for field in fields:
                if not BookField.is_valid(field):
                    valid_fields = ", ".join(BookField.get_all_fields())
                    logger.warning(f"Invalid field name: {field}. Valid fields: {valid_fields}")
                    return {"error": f"Invalid field name: {field}. Valid fields: {valid_fields}"}
                
            return self.helper.get_book_details_filtered(payload["isbn"], fields)
        except Exception as e:
            logger.error(f"Error fetching filtered book details: {str(e)}")
            return {"error": f"Failed to fetch filtered book details: {str(e)}"}
        
    def _get_books_by_author(self, payload: Dict) -> Dict:
        """
        Get all books written by a specific author.
        Handles pagination internally and returns a complete list.
        
        Args:
            payload: Dict containing 'author_name' key and optional 'max_results' integer
            
        Returns:
            Dict containing a list of books and metadata
        """
        try:
            require_keys(payload, ["author_name"])
            author_name = payload["author_name"]
            max_results = payload.get("max_results", 100)
            
            # Log who is making the request
            auth_context = AuthContext.from_payload(payload)
            if auth_context.is_authenticated():
                logger.info(f"User {auth_context.user_id} ({auth_context.role}) searching books by author: {author_name}")
            
            # Ensure max_results is an integer
            try:
                max_results = int(max_results)
                if max_results <= 0:
                    logger.error("Invalid 'max_results' parameter: must be a positive integer")
                    return {"error": "Invalid 'max_results' parameter: must be a positive integer"}
            except ValueError:
                logger.error("Invalid 'max_results' parameter: must be a valid integer")
                return {"error": "Invalid 'max_results' parameter: must be a valid integer"}
            
            return self.helper.get_books_by_author(author_name, max_results)
        except Exception as e:
            logger.error(f"Error fetching books by author: {str(e)}")
            return {"error": f"Failed to fetch books by author: {str(e)}"}
        
    def _get_books_by_author_filtered(self, payload: Dict) -> Dict:
        """
        Get all books written by a specific author with only specified fields.
        
        Args:
            payload: Dict containing 'author_name' key, optional 'fields' list,
                    and optional 'max_results' integer
            
        Returns:
            Dict containing a list of filtered books and metadata
        """
        try:
            require_keys(payload, ["author_name"])
            author_name = payload["author_name"]
            fields = payload.get("fields", BookDefaultFields.DEFAULT_FIELDS)
            max_results = payload.get("max_results", 100)
            
            # Log who is making the request
            user_id = get_authenticated_user_id(payload)
            if user_id:
                logger.info(f"User {user_id} fetching filtered books by author: {author_name}")
            
            # If fields is provided, ensure it's a list
            if not isinstance(fields, list):
                logger.error("Invalid 'fields' parameter: must be a list")
                return {"error": "Invalid 'fields' parameter: must be a list of field names"}
            
            # Validate field names if provided
            for field in fields:
                if not BookField.is_valid(field):
                    valid_fields = ", ".join(BookField.get_all_fields())
                    logger.warning(f"Invalid field name: {field}. Valid fields: {valid_fields}")
                    return {"error": f"Invalid field name: {field}. Valid fields: {valid_fields}"}
            
            # Ensure max_results is an integer
            try:
                max_results = int(max_results)
                if max_results <= 0:
                    logger.error("Invalid 'max_results' parameter: must be a positive integer")
                    return {"error": "Invalid 'max_results' parameter: must be a positive integer"}
            except ValueError:
                logger.error("Invalid 'max_results' parameter: must be a valid integer")
                return {"error": "Invalid 'max_results' parameter: must be a valid integer"}
            
            return self.helper.get_books_by_author_filtered(author_name, fields, max_results)
        except Exception as e:
            logger.error(f"Error fetching filtered books by author: {str(e)}")
            return {"error": f"Failed to fetch filtered books by author: {str(e)}"}
