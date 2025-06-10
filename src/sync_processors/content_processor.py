from typing import Dict, List, Any

import botocore.exceptions

from helpers.common_helper.common_helper import require_keys, Retry
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.app_logic_helpers.content_helper import ContentHelper, ContentValidationError
from sync_processor_registry.processor_registry import ProcessorRegistry
from sync_processors.base_processor import BaseProcessor
from enums.content_status import ContentStatus, WorkflowStatus
from enums.content_type import ContentType

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
            "list_content_by_publisher_and_type": self._list_content_by_publisher_and_type,
            "archive_content": self._archive_content,
            "search_content": self._search_content,
            "query_by_attributes": self._query_by_attributes,
        })
        
    def _validate_workflow_status_fields(self, params_dict: Dict) -> Dict:
        """
        Validate workflow status fields in the provided dictionary.
        
        Args:
            params_dict: Dictionary containing parameters that may include workflow status fields
            
        Returns:
            Error dictionary if validation fails, None if validation passes
        """
        for status_field in WorkflowStatus.WORKFLOW_STATUS_FIELDS:
            if status_field in params_dict and not WorkflowStatus.is_valid(params_dict[status_field]):
                valid_statuses = ", ".join(WorkflowStatus.get_valid_statuses())
                return {"error": f"Invalid {status_field}: {params_dict[status_field]}. Valid values: {valid_statuses}"}
        return None
    
    def _validate_content_status(self, params_dict: Dict) -> Dict:
        """
        Validate content status field in the provided dictionary.
        
        Args:
            params_dict: Dictionary containing parameters that may include content status
            
        Returns:
            Error dictionary if validation fails, None if validation passes
        """
        if "status" in params_dict and not ContentStatus.is_valid(params_dict["status"]):
            valid_statuses = ", ".join(ContentStatus.get_valid_statuses())
            return {"error": f"Invalid status: {params_dict['status']}. Valid statuses: {valid_statuses}"}
        return None
    
    def _validate_content_type(self, params_dict: Dict) -> Dict:
        """
        Validate content type field in the provided dictionary.
        
        Args:
            params_dict: Dictionary containing parameters that may include content type
            
        Returns:
            Error dictionary if validation fails, None if validation passes
        """
        if "type" in params_dict and not ContentType.is_valid(params_dict["type"]):
            valid_types = ", ".join(ContentType.get_valid_types())
            return {"error": f"Invalid type: {params_dict['type']}. Valid types: {valid_types}"}
        return None
    
    def _add_pagination_to_response(self, result: Dict, response: Dict) -> Dict:
        """
        Add pagination details to response if available in the result.
        
        Args:
            result: Result dictionary from helper method
            response: Response dictionary being constructed for API
            
        Returns:
            Updated response with pagination details added if available
        """
        # Add pagination details if available
        if "pagination_token" in result:
            response["pagination"] = {
                "next_token": result["pagination_token"],
                "has_more": result.get("has_more", False)
            }
                
        return response

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
            
            # Convert status string values to enum values if present
            if "status" in payload["updates"]:
                status = payload["updates"]["status"]
                if isinstance(status, str) and ContentStatus.is_valid(status):
                    # Keep as string but validate against enum values
                    pass
                    
            # Convert workflow status string values to enum values if present
            for field in WorkflowStatus.WORKFLOW_STATUS_FIELDS:
                if field in payload["updates"]:
                    status = payload["updates"][field]
                    if isinstance(status, str) and WorkflowStatus.is_valid(status):
                        # Keep as string but validate against enum values
                        pass
                        
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
        - Update status fields: {"content_id": "123", "attribute": "rag_status", "value": WorkflowStatus.ENABLED.value}
        """
        try:
            require_keys(payload, ["content_id", "attribute", "value"])
            
            attribute = payload["attribute"]
            value = payload["value"]
            
            # Validate workflow status attributes against enum values
            if attribute in WorkflowStatus.WORKFLOW_STATUS_FIELDS:
                # Create a temporary dictionary with the attribute and value
                temp_dict = {attribute: value}
                error = self._validate_workflow_status_fields(temp_dict)
                if error:
                    return error
            
            # Validate status attribute against enum values
            if attribute == "status":
                # Create a temporary dictionary with the status and value
                temp_dict = {"status": value}
                error = self._validate_content_status(temp_dict)
                if error:
                    return error
            
            return self.helper.update_content_attribute(
                content_id=payload["content_id"],
                attribute=attribute,
                value=value
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
            
            # Add pagination details using helper method
            response = self._add_pagination_to_response(result, response)
                
            return response
        except Exception as e:
            logger.error(f"Error listing content: {str(e)}")
            return {"error": f"Failed to list content: {str(e)}"}

    def _list_content_by_publisher_and_type(self, payload: Dict) -> Dict:
        """
        List content by publisher and content type with pagination support.
        
        Required payload keys:
        - publisher_id: ID of the publisher to list content for
        - content_type: Content type to filter by (from ContentType enum)
        
        Optional payload keys:
        - limit: Maximum number of items to return
        - pagination_token: Token for retrieving the next page of results
        """
        try:
            require_keys(payload, ["publisher_id", "content_type"])
            
            # Validate content_type parameter
            content_type = payload["content_type"]
            if not ContentType.is_valid(content_type):
                valid_types = ", ".join(ContentType.get_valid_types())
                return {"error": f"Invalid content_type: {content_type}. Valid types: {valid_types}"}
            
            # Extract pagination parameters if provided
            limit = payload.get("limit")
            pagination_token = payload.get("pagination_token")
            
            result = self.helper.list_content_by_publisher_and_type(
                publisher_id=payload["publisher_id"],
                content_type=content_type,
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
            
            # Add pagination details using helper method
            response = self._add_pagination_to_response(result, response)
                
            return response
        except Exception as e:
            logger.error(f"Error listing content by publisher and type: {str(e)}")
            return {"error": f"Failed to list content by publisher and type: {str(e)}"}

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
        - Search by type: {"type": ContentType.BOOK.value}
        - Search by status: {"status": ContentStatus.ACTIVE.value}
        - Search by title pattern: {"title": "python"}
        - Search by metadata: {"metadata.isbn": "1234567890"}
        - Search by workflow status: {"rag_status": WorkflowStatus.ENABLED.value}
        """
        try:
            # Extract pagination parameters
            search_params = payload.copy()
            limit = search_params.pop("limit", None)
            pagination_token = search_params.pop("pagination_token", None)
            
            # Validate status parameters if provided
            error = self._validate_content_status(search_params)
            if error:
                return error
                
            # Validate workflow status parameters if provided
            error = self._validate_workflow_status_fields(search_params)
            if error:
                return error
                    
            # Validate type parameter if provided
            error = self._validate_content_type(search_params)
            if error:
                return error
            
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
            
            # Add pagination details using helper method
            response = self._add_pagination_to_response(search_result, response)
                
            return response
        except Exception as e:
            logger.error(f"Error searching content: {str(e)}")
            return {"error": f"Failed to search content: {str(e)}"}


            
    def _query_by_attributes(self, payload: Dict) -> Dict:
        """
        Query content by multiple attributes simultaneously with pagination support.
        
        Required payload keys:
        - attributes: Dictionary of attribute-value pairs to filter by
        
        Optional payload keys:
        - limit: Maximum number of items to return
        - pagination_token: Token for retrieving the next page of results
        
        Example payload:
        {
            "attributes": {
                "publisher_id": "publisher-123",
                "type": "BOOK",
                "status": "ACTIVE"
            },
            "limit": 10,
            "pagination_token": "base64encodedtoken"
        }
        """
        try:
            require_keys(payload, ["attributes"])
            
            # Make sure attributes is a dictionary
            attributes = payload.get("attributes")
            if not isinstance(attributes, dict):
                return {"error": "The 'attributes' field must be a dictionary of attribute-value pairs"}
                
            # Extract pagination parameters if provided
            limit = payload.get("limit")
            pagination_token = payload.get("pagination_token")
            
            # Validate each attribute according to its type
            search_params = attributes.copy()
            
            # Validate status parameter if provided
            error = self._validate_content_status(search_params)
            if error:
                return error
                
            # Validate workflow status parameters if provided
            error = self._validate_workflow_status_fields(search_params)
            if error:
                return error
                    
            # Validate type parameter if provided
            error = self._validate_content_type(search_params)
            if error:
                return error
            
            # Execute search with the provided attributes
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
            
            # Add pagination details using helper method
            response = self._add_pagination_to_response(search_result, response)
                
            return response
        except Exception as e:
            logger.error(f"Error querying content by attributes: {str(e)}")
            return {"error": f"Failed to query content by attributes: {str(e)}"}
