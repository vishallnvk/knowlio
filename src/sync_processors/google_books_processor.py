"""
Processor for Google Books API operations.
Provides actions to fetch and filter book details by ISBN.
"""

from typing import Dict, List, Optional

from helpers.common_helper.common_helper import require_keys
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.app_logic_helpers.google_books_helper import GoogleBooksHelper
from sync_processor_registry.processor_registry import ProcessorRegistry
from sync_processors.base_processor import BaseProcessor

logger = LoggerHelper(__name__).get_logger()


@ProcessorRegistry.register("google_books")
class GoogleBooksProcessor(BaseProcessor):
    def __init__(self):
        self.helper = GoogleBooksHelper()
        super().__init__({
            "get_book_details": self._get_book_details,
            "get_book_details_filtered": self._get_book_details_filtered,
        })

    def _get_book_details(self, payload: Dict) -> Dict:
        """
        Get complete book details from Google Books API by ISBN.
        
        Args:
            payload: Dict containing 'isbn' key
            
        Returns:
            Dict containing book details or error message
        """
        require_keys(payload, ["isbn"])
        return self.helper.get_book_details(payload["isbn"])

    def _get_book_details_filtered(self, payload: Dict) -> Dict:
        """
        Get filtered book details from Google Books API by ISBN.
        
        Args:
            payload: Dict containing 'isbn' key and optional 'fields' list
            
        Returns:
            Dict containing filtered book details or error message
        """
        require_keys(payload, ["isbn"])
        fields = payload.get("fields")
        
        # If fields is provided, ensure it's a list
        if fields is not None and not isinstance(fields, list):
            logger.error("Invalid 'fields' parameter: must be a list")
            return {"error": "Invalid 'fields' parameter: must be a list of field names"}
            
        return self.helper.get_book_details_filtered(payload["isbn"], fields)
