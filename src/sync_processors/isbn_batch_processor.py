"""
Processor for batch processing ISBNs from CSV files and inserting book metadata into OpenSearch.
"""

import csv
import io
import base64
import concurrent.futures
import json
from typing import Dict, List, Any, Optional
import time

from helpers.common_helper.common_helper import require_keys
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.app_logic_helpers.google_books_helper import GoogleBooksHelper
from helpers.aws_service_helpers.opensearch_helper import OpenSearchHelper
from sync_processor_registry.processor_registry import ProcessorRegistry
from sync_processors.base_processor import BaseProcessor
from models.book_model import BookModel

logger = LoggerHelper(__name__).get_logger()


@ProcessorRegistry.register("isbn_batch")
class ISBNBatchProcessor(BaseProcessor):
    def __init__(self):
        self.google_books_helper = GoogleBooksHelper()
        self.opensearch_helper = OpenSearchHelper()
        
        # Default index for storing book metadata
        self.books_index = "books-index"
        
        # Configure batch processing parameters
        self.max_workers = 10  # Maximum number of parallel workers
        self.batch_size = 25   # Number of ISBNs to process per batch
        
        super().__init__({
            "process_isbn_list": self._process_isbn_list,
            "get_processing_status": self._get_processing_status
        })
        
        # Store processing statistics
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "processing_time": 0
        }

    def _process_isbn_list(self, payload: Dict) -> Dict[str, Any]:
        """
        Process a list of ISBNs and store book metadata in OpenSearch.
        
        Args:
            payload: Dict containing:
                - 'isbns': List of ISBN strings
                - 'index_name': (Optional) OpenSearch index name to use
        
        Returns:
            Dict with processing statistics
        """
        start_time = time.time()
        require_keys(payload, ["isbns"])
        
        # Extract parameters
        isbns = payload["isbns"]
        
        if not isinstance(isbns, list):
            logger.error("isbns parameter must be a list")
            return {"error": "isbns parameter must be a list"}
        
        if not isbns:
            return {"error": "Empty ISBN list provided"}
        
        # Process the ISBNs
        result = self._process_isbns(isbns)
        
        # Update stats
        self.stats["processing_time"] = time.time() - start_time
        
        return {
            "message": f"Processed {len(isbns)} ISBNs",
            "stats": self.stats,
            "details": result
        }

    def _get_processing_status(self, payload: Dict) -> Dict[str, Any]:
        """
        Get the current processing statistics.
        
        Args:
            payload: Not used
            
        Returns:
            Dict with processing statistics
        """
        return {"stats": self.stats}

    def _process_isbns(self, isbns: List[str]) -> Dict[str, Any]:
        """
        Process a list of ISBNs in parallel batches.
        
        Args:
            isbns: List of ISBNs to process
            index_name: OpenSearch index name to use
            
        Returns:
            Dict with processing results
        """
        # Reset stats for this processing run
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "processing_time": 0
        }
        
        # Split ISBNs into batches
        batches = [isbns[i:i + self.batch_size] for i in range(0, len(isbns), self.batch_size)]
        results = {"successful_isbns": [], "failed_isbns": []}
        
        # Ensure we have a valid index for storing book data
        self._ensure_books_index_exists(index_name)
        
        # Process batches in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all batches for processing
            future_to_batch = {
                executor.submit(self._process_isbn_batch, batch, index_name): batch 
                for batch in batches
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_batch):
                batch_result = future.result()
                results["successful_isbns"].extend(batch_result["successful_isbns"])
                results["failed_isbns"].extend(batch_result["failed_isbns"])
                
                # Update overall stats
                self.stats["total_processed"] += batch_result["total"]
                self.stats["successful"] += batch_result["successful"]
                self.stats["failed"] += batch_result["failed"]
        
        return results

    def _process_isbn_batch(self, isbns: List[str], index_name: str) -> Dict[str, Any]:
        """
        Process a batch of ISBNs: fetch metadata and store in OpenSearch.
        
        Args:
            isbns: List of ISBNs to process
            index_name: OpenSearch index name to use
            
        Returns:
            Dict with batch processing results
        """
        batch_result = {
            "total": len(isbns),
            "successful": 0,
            "failed": 0,
            "successful_isbns": [],
            "failed_isbns": []
        }
        
        book_documents = []
        
        # Process each ISBN in the batch
        for isbn in isbns:
            try:
                # Fetch book details from Google Books API
                book_data = self.google_books_helper.get_book_details(isbn)
                
                # Check if error was returned
                if "error" in book_data:
                    logger.warning(f"Failed to get metadata for ISBN {isbn}: {book_data['error']}")
                    batch_result["failed"] += 1
                    batch_result["failed_isbns"].append({"isbn": isbn, "reason": book_data["error"]})
                    continue
                
                # Add to documents for bulk indexing
                book_documents.append(book_data)
                batch_result["successful"] += 1
                batch_result["successful_isbns"].append({"isbn": isbn, "title": book_data.get("title")})
                
            except Exception as e:
                logger.error(f"Error processing ISBN {isbn}: {str(e)}")
                batch_result["failed"] += 1
                batch_result["failed_isbns"].append({"isbn": isbn, "reason": str(e)})
        
        # Bulk index to OpenSearch if we have any successful documents
        if book_documents:
            try:
                self._bulk_index_books(book_documents, index_name)
            except Exception as e:
                logger.error(f"Failed to bulk index books: {str(e)}")
                # Mark all books as failed if bulk indexing failed
                batch_result["failed"] += batch_result["successful"]
                batch_result["successful"] = 0
                batch_result["failed_isbns"].extend([
                    {"isbn": doc.get("isbn"), "reason": "Bulk indexing failed"} 
                    for doc in book_documents
                ])
                batch_result["successful_isbns"] = []
        
        return batch_result

    def _ensure_books_index_exists(self, index_name: str):
        """
        Make sure the books index exists or create it with proper mapping.
        
        Args:
            index_name: Name of the OpenSearch index to check/create
        """
        try:
            # Check if the index exists
            response = self.opensearch_helper.get_index_settings(index_name)
            logger.info(f"Index {index_name} already exists")
            return
        except Exception:
            # Index doesn't exist, create it
            logger.info(f"Creating index {index_name}")
            
            # Define mapping for book fields
            mapping = {
                "mappings": {
                    "properties": {
                        "id": {"type": "keyword"},
                        "isbn": {"type": "keyword"},
                        "title": {"type": "text", "analyzer": "standard", "fields": {"keyword": {"type": "keyword"}}},
                        "authors": {"type": "text", "analyzer": "standard", "fields": {"keyword": {"type": "keyword"}}},
                        "publisher": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                        "published_date": {"type": "date", "format": "yyyy||yyyy-MM||yyyy-MM-dd||strict_date_optional_time"},
                        "description": {"type": "text", "analyzer": "standard"},
                        "page_count": {"type": "integer"},
                        "categories": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                        "language": {"type": "keyword"},
                        "average_rating": {"type": "float"},
                        "ratings_count": {"type": "integer"},
                        "maturity_rating": {"type": "keyword"},
                        "image_links": {"type": "object"},
                        "source": {"type": "keyword"},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"}
                    }
                },
                "settings": {
                    "index": {
                        "number_of_shards": 3,
                        "number_of_replicas": 1
                    }
                }
            }
            
            try:
                self.opensearch_helper.create_index(index_name, mapping)
                logger.info(f"Successfully created index {index_name}")
            except Exception as e:
                logger.error(f"Failed to create index {index_name}: {str(e)}")
                raise

    def _bulk_index_books(self, book_documents: List[Dict], index_name: str):
        """
        Bulk index book documents to OpenSearch.
        
        Args:
            book_documents: List of book data dictionaries
            index_name: Name of the OpenSearch index to index into
        """
        # Add timestamps to each document
        timestamp = int(time.time() * 1000)
        for doc in book_documents:
            doc["created_at"] = timestamp
            doc["updated_at"] = timestamp
        
        # Use bulk_index method from the helper
        response = self.opensearch_helper.bulk_index(
            index_name=index_name,
            documents=book_documents,
            id_field="isbn"  # Use ISBN as document ID
        )
        
        # Check for errors in the response
        if response.get("errors", False):
            error_items = [item for item in response.get("items", []) if "error" in item.get("index", {})]
            if error_items:
                error_details = error_items[0].get("index", {}).get("error", {})
                logger.error(f"Bulk indexing had errors: {error_details}")
                raise Exception(f"Bulk indexing failed: {error_details}")
        
        logger.info(f"Successfully indexed {len(book_documents)} books to {index_name}")
