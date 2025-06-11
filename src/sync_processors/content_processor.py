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
            "archive_content": self._archive_content,
            "search_content": self._search_content,
        })
        
    def _validate_workflow_status_fields(self, params_dict: Dict) -> Dict:
        """
        Validate workflow status fields in the provided dictionary.
        
        Args:
            params_dict: Dictionary containing parameters that may include workflow status fields
            
        Returns:
            Error dictionary if validation fails, None if validation passes
        """
        # Define the workflow status fields directly to avoid issues with the enum
        status_fields = ["rag_status", "training_status", "licensing_status"]
        
        for status_field in status_fields:
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
            # Use the direct list instead of the enum attribute to avoid iteration errors
            status_fields = ["rag_status", "training_status", "licensing_status"]
            for field in status_fields:
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
        Unified search method for content that handles all supported formats:
        1. list_content_by_publisher: {"publisher_id": "pub123", ...}
        2. list_content_by_publisher_and_type: {"publisher_id": "pub123", "content_type": "BOOK", ...}
        3. search_content: {any field combinations without the attributes wrapper}
        4. Legacy format: {"attributes": {field combinations}, ...}
        
        All formats support pagination with:
        - limit: Maximum number of items to return
        - pagination_token: Token for retrieving the next page of results
        """
        try:
            # Handle different payload formats based on the action that was called
            action = payload.get("__action__", "search_content")
            search_params = {}
            limit = payload.get("limit")
            pagination_token = payload.get("pagination_token")
            
            # Format 1: list_content_by_publisher
            if action == "list_content_by_publisher":
                require_keys(payload, ["publisher_id"])
                search_params = {"publisher_id": payload["publisher_id"]}
            
            # Format 2: list_content_by_publisher_and_type
            elif action == "list_content_by_publisher_and_type":
                require_keys(payload, ["publisher_id", "content_type"])
                content_type = payload["content_type"]
                
                # Validate content_type parameter
                if not ContentType.is_valid(content_type):
                    valid_types = ", ".join(ContentType.get_valid_types())
                    return {"error": f"Invalid content_type: {content_type}. Valid types: {valid_types}"}
                
                search_params = {
                    "publisher_id": payload["publisher_id"],
                    "type": content_type
                }
                
            # Format 3: search_content (direct parameters)
            elif action == "search_content":
                # Check for attributes format first (legacy support)
                if "attributes" in payload:
                    attributes = payload.get("attributes")
                    if not isinstance(attributes, dict):
                        return {"error": "The 'attributes' field must be a dictionary of attribute-value pairs"}
                    search_params = attributes.copy()
                else:
                    # Use all parameters directly as search criteria
                    search_params = payload.copy()
                    # Remove pagination parameters
                    search_params.pop("limit", None)
                    search_params.pop("pagination_token", None)
                    search_params.pop("__action__", None)
            
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
            
            # Convert result structure to standardized format including pagination
            response = {
                "contents": search_result.get("items", []),
                "count": search_result.get("count", 0),
                "total_scanned": search_result.get("total_scanned", 0)
            }
            
            # Include pagination information directly in response
            if "pagination" in search_result:
                response["pagination"] = search_result["pagination"]
                
            return response
        except Exception as e:
            logger.error(f"Error searching content: {str(e)}")
            return {"error": f"Failed to search content: {str(e)}"}
