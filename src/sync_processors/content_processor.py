from typing import Dict, List, Any

import botocore.exceptions

from helpers.common_helper.common_helper import require_keys, Retry
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.app_logic_helpers.content_helper import ContentHelper, ContentValidationError
from sync_processor_registry.processor_registry import ProcessorRegistry
from sync_processors.base_processor import BaseProcessor

logger = LoggerHelper(__name__).get_logger()

@ProcessorRegistry.register("content")
class ContentProcessor(BaseProcessor):
    def __init__(self):
        self.helper = ContentHelper()
        super().__init__({
            "upload_content_metadata": self._upload_content_metadata,
            "upload_content_blob": self._upload_content_blob,
            "get_content_details": self._get_content_details,
            "update_content_metadata": self._update_content_metadata,
            "update_content_attribute": self._update_content_attribute,
            "list_content_by_publisher": self._list_content_by_publisher,
            "archive_content": self._archive_content,
            "search_content": self._search_content,
            "query_by_attribute": self._query_by_attribute,
        })

    def _upload_content_metadata(self, payload: Dict) -> Dict:
        """
        Create a new content entry with metadata.
        
        Required payload keys:
        - publisher_id: ID of the content publisher
        - title: Content title
        - type: Content type (BOOK, VIDEO, AUDIO, DATASET, TEXT)
        
        Optional payload keys:
        - tags: List of content tags
        - description: Content description
        - metadata: Type-specific metadata
        """
        try:
            require_keys(payload, ["publisher_id", "title", "type"])
            return self.helper.upload_content_metadata(payload)
        except ContentValidationError as e:
            logger.warning(f"Content validation error: {str(e)}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Error uploading content metadata: {str(e)}")
            return {"error": f"Failed to upload content metadata: {str(e)}"}

    def _upload_content_blob(self, payload: Dict) -> Dict:
        """
        Attach a blob file to existing content and activate it.
        
        Required payload keys:
        - content_id: ID of the content to update
        - s3_uri: S3 key for the uploaded file
        """
        try:
            require_keys(payload, ["content_id", "s3_uri"])
            return self.helper.upload_content_blob(payload["content_id"], payload["s3_uri"])
        except ContentValidationError as e:
            logger.warning(f"Content validation error: {str(e)}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Error uploading content blob: {str(e)}")
            return {"error": f"Failed to upload content blob: {str(e)}"}

    def _get_content_details(self, payload: Dict) -> Dict:
        """
        Get content details by ID.
        
        Required payload keys:
        - content_id: ID of the content to fetch
        """
        try:
            require_keys(payload, ["content_id"])
            content = self.helper.get_content_details(payload["content_id"])
            
            if not content:
                return {"error": f"Content not found with ID: {payload['content_id']}"}
                
            return content
        except Exception as e:
            logger.error(f"Error fetching content: {str(e)}")
            return {"error": f"Failed to fetch content: {str(e)}"}

    def _update_content_metadata(self, payload: Dict) -> Dict:
        """
        Update content metadata with validation.
        
        Required payload keys:
        - content_id: ID of the content to update
        - updates: Dict of fields to update
        """
        try:
            require_keys(payload, ["content_id", "updates"])
            return self.helper.update_content_metadata(payload["content_id"], payload["updates"])
        except ContentValidationError as e:
            logger.warning(f"Content validation error: {str(e)}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Error updating content: {str(e)}")
            return {"error": f"Failed to update content: {str(e)}"}

    def _update_content_attribute(self, payload: Dict) -> Dict:
        """
        Update a single attribute of content, including nested fields.
        
        Required payload keys:
        - content_id: ID of the content to update
        - attribute: Attribute name (can use dot notation for nested fields)
        - value: New value for the attribute
        
        Examples:
        - Update title: {"content_id": "123", "attribute": "title", "value": "New Title"}
        - Update metadata field: {"content_id": "123", "attribute": "metadata.isbn", "value": "1234567890"}
        - Update status fields: {"content_id": "123", "attribute": "rag_status", "value": "ENABLED"}
        """
        try:
            require_keys(payload, ["content_id", "attribute", "value"])
            return self.helper.update_content_attribute(
                content_id=payload["content_id"],
                attribute=payload["attribute"],
                value=payload["value"]
            )
        except ContentValidationError as e:
            logger.warning(f"Content validation error: {str(e)}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Error updating content attribute: {str(e)}")
            return {"error": f"Failed to update content attribute: {str(e)}"}

    def _list_content_by_publisher(self, payload: Dict) -> Dict:
        """
        List content by publisher with pagination support.
        
        Required payload keys:
        - publisher_id: ID of the publisher to list content for
        
        Optional payload keys:
        - limit: Maximum number of items to return
        - pagination_token: Token for retrieving the next page of results
        """
        try:
            require_keys(payload, ["publisher_id"])
            
            # Extract pagination parameters if provided
            limit = payload.get("limit")
            pagination_token = payload.get("pagination_token")
            
            result = self.helper.list_content_by_publisher(
                publisher_id=payload["publisher_id"],
                limit=limit,
                pagination_token=pagination_token
            )
            
            # Handle error case
            if "error" in result:
                return {"error": result["error"]}
            
            # Convert result structure to standardized format
            response = {
                "contents": result.get("items", []),
                "count": result.get("count", 0)
            }
            
            # Add pagination details if available
            if "pagination_token" in result:
                response["pagination"] = {
                    "next_token": result["pagination_token"],
                    "has_more": result.get("has_more", False)
                }
                
            return response
        except Exception as e:
            logger.error(f"Error listing content: {str(e)}")
            return {"error": f"Failed to list content: {str(e)}"}

    def _archive_content(self, payload: Dict) -> Dict:
        """
        Archive content by setting its status to ARCHIVED.
        
        Required payload keys:
        - content_id: ID of the content to archive
        """
        try:
            require_keys(payload, ["content_id"])
            return self.helper.archive_content(payload["content_id"])
        except ContentValidationError as e:
            logger.warning(f"Content validation error: {str(e)}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Error archiving content: {str(e)}")
            return {"error": f"Failed to archive content: {str(e)}"}
        
    def _search_content(self, payload: Dict) -> Dict:
        """
        Search for content based on flexible parameters with pagination support.
        
        Optional payload keys:
        - Any combination of content fields or metadata
        - limit: Maximum number of results to return
        - pagination_token: Token for retrieving the next page of results
                
        Examples:
        - Search by type: {"type": "BOOK"}
        - Search by status: {"status": "ACTIVE"}
        - Search by title pattern: {"title": "python"}
        - Search by metadata: {"metadata.isbn": "1234567890"}
        - Search by workflow status: {"rag_status": "ENABLED"}
        """
        try:
            # Extract pagination parameters
            search_params = payload.copy()
            limit = search_params.pop("limit", None)
            pagination_token = search_params.pop("pagination_token", None)
            
            # Execute search with remaining parameters as filters
            search_result = self.helper.search_content(
                search_params=search_params,
                limit=limit,
                pagination_token=pagination_token
            )
            
            # Handle error case
            if "error" in search_result:
                return {"error": search_result["error"]}
            
            # Convert result structure to standardized format
            response = {
                "contents": search_result.get("items", []),
                "count": search_result.get("count", 0),
                "total_scanned": search_result.get("total_scanned", 0)
            }
            
            # Add pagination details if available
            if "pagination_token" in search_result:
                response["pagination"] = {
                    "next_token": search_result["pagination_token"],
                    "has_more": search_result.get("has_more", False)
                }
                
            return response
        except Exception as e:
            logger.error(f"Error searching content: {str(e)}")
            return {"error": f"Failed to search content: {str(e)}"}

    def _query_by_attribute(self, payload: Dict) -> Dict:
        """
        Generic attribute-based query method.
        
        Required payload keys:
        - attribute: Attribute name to query by
        - value: Value to match
        
        Optional payload keys:
        - limit: Maximum number of results to return
        - pagination_token: Token for retrieving the next page of results
        
        Examples:
        - Query by workflow status: {"attribute": "rag_status", "value": "ENABLED"}
        - Query by content type: {"attribute": "type", "value": "BOOK"}
        """
        try:
            require_keys(payload, ["attribute", "value"])
            
            # Extract parameters
            attribute = payload["attribute"]
            value = payload["value"]
            limit = payload.get("limit")
            pagination_token = payload.get("pagination_token")
            
            # Perform the query
            result = self.helper.query_by_attribute(
                attribute=attribute,
                value=value,
                limit=limit,
                pagination_token=pagination_token
            )
            
            # Handle error case
            if "error" in result:
                return {"error": result["error"]}
            
            # Convert result structure to standardized format
            response = {
                "contents": result.get("items", []),
                "count": result.get("count", 0),
                "total_scanned": result.get("total_scanned", 0)
            }
            
            # Add pagination details if available
            if "pagination_token" in result:
                response["pagination"] = {
                    "next_token": result["pagination_token"],
                    "has_more": result.get("has_more", False)
                }
                
            return response
        except Exception as e:
            logger.error(f"Error querying content: {str(e)}")
            return {"error": f"Failed to query content: {str(e)}"}
