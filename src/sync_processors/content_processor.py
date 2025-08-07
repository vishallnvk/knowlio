from typing import Dict, List, Any

import botocore.exceptions

from helpers.common_helper.common_helper import require_keys, Retry
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.common_helper.auth_helper import require_role, get_authenticated_user_id
from helpers.common_helper.auth_context import AuthContext
from helpers.common_helper.response_formatter import ResponseFormatter
from helpers.common_helper.data_type_utils import DataTypeUtils
from helpers.common_helper.database_operation_wrapper import DatabaseOperationWrapper
from helpers.app_logic_helpers.content_helper import ContentHelper, ContentValidationError
from helpers.app_logic_helpers.google_books_helper import GoogleBooksHelper
from sync_processor_registry.processor_registry import ProcessorRegistry
from sync_processors.base_processor import BaseProcessor
from enums.content_status import ContentStatus, WorkflowStatus
from enums.content_type import ContentType
from models.content_model import ContentModel
from models.content_factory import ContentFactory
from config.content_config import WORKFLOW_STATUS_FIELDS

logger = LoggerHelper(__name__).get_logger()

@ProcessorRegistry.register("content")
class ContentProcessor(BaseProcessor):
    def __init__(self):
        self.helper = ContentHelper()
        self.google_books_helper = GoogleBooksHelper()
        self.db_wrapper = DatabaseOperationWrapper()
        super().__init__({
            "upload_content_metadata": self._upload_content_metadata,
            "upload_content_blob": self._upload_content_blob,
            "get_content_details": self._get_content_details,
            "update_content_metadata": self._update_content_metadata,
            "update_content_attribute": self._update_content_attribute,
            "archive_content": self._archive_content,
            "search_content": self._search_content,
            "get_content_count": self._get_content_count,
        })
        
    def _validate_workflow_status_fields(self, params_dict: Dict) -> Dict:
        """
        Validate workflow status fields in the provided dictionary.
        
        Args:
            params_dict: Dictionary containing parameters that may include workflow status fields
            
        Returns:
            Error dictionary if validation fails, None if validation passes
        """
        for status_field in WORKFLOW_STATUS_FIELDS:
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
        if "type" in params_dict:
            supported_types = ContentFactory.get_supported_types()
            if params_dict["type"].upper() not in supported_types:
                return {"error": f"Invalid type: {params_dict['type']}. Valid types: {', '.join(supported_types)}"}
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
        Create a new content entry with metadata using the appropriate content type model.
        
        Required payload keys:
        - type: Content type (BOOK, AUDIO, etc.)
        
        For BOOK type, two modes supported:
        
        Mode 1 - ISBN Only (Recommended):
        - isbn: ISBN number (system will fetch all other details from Google Books API)
        
        Mode 2 - Full Details:
        - authors: List of authors
        - year: Publication year
        - isbn: ISBN number
        - title: Book title
        - keywords: List of keywords
        
        Optional keys for BOOK:
        - rag_status: RAG workflow status (ENABLED/DISABLED, default: DISABLED)
        - training_status: Training workflow status (ENABLED/DISABLED, default: DISABLED)
        - licensing_status: Licensing workflow status (ENABLED/DISABLED, default: DISABLED)
        """
        try:
            require_keys(payload, ["type"])
            
            # Validate content type
            error = self._validate_content_type(payload)
            if error:
                message, code = ResponseFormatter.extract_error_info(error)
                return ResponseFormatter.format_error(message, ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
            
            # Special handling for BOOK type with ISBN-only uploads
            if payload["type"].upper() == "BOOK" and self._is_isbn_only_upload(payload):
                logger.info("Detected ISBN-only book upload, fetching details from Google Books API")
                payload = self._enrich_book_from_isbn(payload)
                
                # Check if enrichment failed
                if "error" in payload:
                    return ResponseFormatter.format_error(
                        payload["error"], 
                        ResponseFormatter.ERROR_CODES["EXTERNAL_SERVICE_ERROR"]
                    )
            
            # Validate workflow status fields if present
            error = self._validate_workflow_status_fields(payload)
            if error:
                message, code = ResponseFormatter.extract_error_info(error)
                return ResponseFormatter.format_error(message, ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
            
            # Add authenticated user info for audit trail if available
            auth_context = AuthContext.from_payload(payload)
            if auth_context.is_authenticated():
                # Add user_id from authenticated user
                payload["user_id"] = auth_context.user_id
                logger.info(f"User {auth_context.user_id} ({auth_context.role}) creating {payload['type']} content")
                
                # Fetch user's AI consent preferences as defaults for content status fields
                user_processor = ProcessorRegistry.get_processor("user")
                if user_processor is not None:
                    try:
                        consent_result = user_processor._get_ai_consent_attributes(payload)
                        
                        if consent_result.get("success") and consent_result.get("data"):
                            consent_data = consent_result["data"]
                            
                            # Map user consent preferences to content status fields
                            # Only set defaults if not explicitly provided in payload
                            if "training_status" not in payload:
                                payload["training_status"] = "ENABLED" if consent_data.get("ai_training_consent", False) else "DISABLED"
                            
                            if "rag_status" not in payload:
                                payload["rag_status"] = "ENABLED" if consent_data.get("ai_reference_consent", False) else "DISABLED"
                            
                            if "licensing_status" not in payload:
                                payload["licensing_status"] = "ENABLED" if consent_data.get("ai_marketplace_consent", False) else "DISABLED"
                            
                            logger.info(f"Applied user's AI consent preferences as defaults for content status fields")
                        else:
                            logger.warning(f"Failed to retrieve user consent preferences: {consent_result.get('error', 'Unknown error')}")
                    except Exception as e:
                        logger.error(f"Error fetching user consent preferences: {str(e)}. Using default consent settings.")
                else:
                    logger.warning("User processor not available, using default consent settings for content status fields")
            
            # Create the appropriate content model using the factory
            try:
                content = ContentFactory.create_content(payload["type"], payload)
            except ValueError as e:
                return ResponseFormatter.format_error(str(e), ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
            
            # Convert content model to dict and save to database
            content_dict = content.to_dict()
            
            # Save to database using the content helper
            result = self.helper.upload_content_metadata(content_dict)
            
            # Handle error response from helper
            if "error" in result:
                message, code = ResponseFormatter.extract_error_info(result)
                return ResponseFormatter.format_error(message, code)
            
            # Format successful create response
            return ResponseFormatter.format_create_response(
                resource_type="content",
                resource_id=result.get("content_id"),
                resource_data=content_dict
            )
            
        except ContentValidationError as e:
            logger.warning(f"Content validation error: {str(e)}")
            return ResponseFormatter.format_error(str(e), ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
        except Exception as e:
            logger.error(f"Error uploading content metadata: {str(e)}")
            return ResponseFormatter.format_error(f"Failed to upload content metadata: {str(e)}", 
                                               ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])

    def _upload_content_blob(self, payload: Dict) -> Dict:
        """
        Attach a blob file to existing content and activate it.
        
        Required payload keys:
        - content_id: ID of the content to update
        - s3_uri: S3 key for the uploaded file
        """
        try:
            require_keys(payload, ["content_id", "s3_uri"])
            result = self.helper.upload_content_blob(payload["content_id"], payload["s3_uri"])
            
            # Handle error response from helper
            if "error" in result:
                message, code = ResponseFormatter.extract_error_info(result)
                return ResponseFormatter.format_error(message, code)
            
            # Format successful update response
            return ResponseFormatter.format_update_response(
                resource_type="content",
                resource_id=payload["content_id"],
                updated_resource=result
            )
        except ContentValidationError as e:
            logger.warning(f"Content validation error: {str(e)}")
            return ResponseFormatter.format_error(str(e), ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
        except Exception as e:
            logger.error(f"Error uploading content blob: {str(e)}")
            return ResponseFormatter.format_error(f"Failed to upload content blob: {str(e)}", 
                                               ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])

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
                return ResponseFormatter.format_error(
                    f"Content not found with ID: {payload['content_id']}", 
                    ResponseFormatter.ERROR_CODES["NOT_FOUND"]
                )
            
            # Format successful response with content data
            return ResponseFormatter.format_success(content)
        except Exception as e:
            logger.error(f"Error fetching content: {str(e)}")
            return ResponseFormatter.format_error(f"Failed to fetch content: {str(e)}", 
                                               ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])

    def _update_content_metadata(self, payload: Dict) -> Dict:
        """
        Update content metadata with validation.
        
        Required payload keys:
        - content_id: ID of the content to update
        - updates: Dict of fields to update
        """
        try:
            require_keys(payload, ["content_id", "updates"])
            
            # Validate workflow status fields if present in updates
            error = self._validate_workflow_status_fields(payload["updates"])
            if error:
                message, code = ResponseFormatter.extract_error_info(error)
                return ResponseFormatter.format_error(message, ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
            
            # Add authenticated user info for audit trail
            user_id = get_authenticated_user_id(payload)
            if user_id:
                # Add modification information to metadata
                updates = payload["updates"]
                if "metadata" not in updates:
                    updates["metadata"] = {}
                
                updates["metadata"]["last_modified_by"] = user_id
                updates["metadata"]["last_modified_at"] = Retry.get_iso_timestamp()
                
                logger.info(f"User {user_id} updating content {payload['content_id']}")
            
            result = self.helper.update_content_metadata(payload["content_id"], payload["updates"])
            
            # Handle error response from helper
            if "error" in result:
                message, code = ResponseFormatter.extract_error_info(result)
                return ResponseFormatter.format_error(message, code)
            
            # Format successful update response
            return ResponseFormatter.format_update_response(
                resource_type="content",
                resource_id=payload["content_id"],
                updated_resource=result
            )
        except ContentValidationError as e:
            logger.warning(f"Content validation error: {str(e)}")
            return ResponseFormatter.format_error(str(e), ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
        except Exception as e:
            logger.error(f"Error updating content: {str(e)}")
            return ResponseFormatter.format_error(f"Failed to update content: {str(e)}", 
                                               ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])

    def _update_content_attribute(self, payload: Dict) -> Dict:
        """
        Update a single attribute of content, including nested fields.
        
        Required payload keys:
        - content_id: ID of the content to update
        - attribute: Attribute name (can use dot notation for nested fields)
        - value: New value for the attribute
        
        Examples:
        - Update title: {"content_id": "123", "attribute": "title", "value": "New Title"}
        - Update status fields: {"content_id": "123", "attribute": "rag_status", "value": "ENABLED"}
        """
        try:
            require_keys(payload, ["content_id", "attribute", "value"])
            
            # Apply type-safe data processing to the entire payload
            safe_payload = self.db_wrapper.safe_process_payload(payload)
            
            attribute = safe_payload["attribute"]
            value = safe_payload["value"]
            
            # Validate workflow status attributes against enum values
            if attribute in WORKFLOW_STATUS_FIELDS:
                # Create a temporary dictionary with the attribute and value
                temp_dict = {attribute: value}
                error = self._validate_workflow_status_fields(temp_dict)
                if error:
                    message, code = ResponseFormatter.extract_error_info(error)
                    return ResponseFormatter.format_error(message, ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
            
            # Validate status attribute against enum values
            if attribute == "status":
                # Create a temporary dictionary with the status and value
                temp_dict = {"status": value}
                error = self._validate_content_status(temp_dict)
                if error:
                    message, code = ResponseFormatter.extract_error_info(error)
                    return ResponseFormatter.format_error(message, ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
            
            # Apply type-safe processing to auth_context if present
            if "auth_context" in safe_payload:
                safe_payload["auth_context"] = self._process_auth_context_safely(safe_payload["auth_context"])
            
            result = self.helper.update_content_attribute(
                content_id=safe_payload["content_id"],
                attribute=attribute,
                value=value
            )
            
            # Handle error response from helper
            if "error" in result:
                message, code = ResponseFormatter.extract_error_info(result)
                return ResponseFormatter.format_error(message, code)
            
            # Format successful update response
            return ResponseFormatter.format_update_response(
                resource_type="content",
                resource_id=safe_payload["content_id"],
                updated_resource=result
            )
        except ContentValidationError as e:
            logger.warning(f"Content validation error: {str(e)}")
            return ResponseFormatter.format_error(str(e), ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
        except Exception as e:
            logger.error(f"Error updating content attribute: {str(e)}")
            return ResponseFormatter.format_error(f"Failed to update content attribute: {str(e)}", 
                                               ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])

    @require_role(["ADMIN", "PUBLISHER"])
    def _archive_content(self, payload: Dict) -> Dict:
        """
        Archive content by setting its status to ARCHIVED.
        Requires ADMIN or PUBLISHER role.
        
        Required payload keys:
        - content_id: ID of the content to archive
        """
        try:
            require_keys(payload, ["content_id"])
            
            # Get authenticated user from context
            auth_context = AuthContext.from_payload(payload)
            logger.info(f"User {auth_context.user_id} ({auth_context.role}) archiving content {payload['content_id']}")
            
            # First update with archival audit information
            updates = {
                "metadata": {
                    "archived_by": auth_context.user_id,
                    "archived_at": Retry.get_iso_timestamp()
                }
            }
            
            self.helper.update_content_metadata(payload["content_id"], updates)
            
            # Then perform the actual archival
            result = self.helper.archive_content(payload["content_id"])
            
            # Handle error response from helper
            if "error" in result:
                message, code = ResponseFormatter.extract_error_info(result)
                return ResponseFormatter.format_error(message, code)
            
            # Format successful archive response
            return ResponseFormatter.format_delete_response(
                resource_type="content",
                resource_id=payload["content_id"]
            )
        except ContentValidationError as e:
            logger.warning(f"Content validation error: {str(e)}")
            return ResponseFormatter.format_error(str(e), ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
        except Exception as e:
            logger.error(f"Error archiving content: {str(e)}")
            return ResponseFormatter.format_error(f"Failed to archive content: {str(e)}", 
                                               ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])
        
    def _search_content(self, payload: Dict) -> Dict:
        """
        Unified search method for content that handles all supported formats:
        1. list_content_by_user: {"user_id": "user123", ...}
        2. list_content_by_user_and_type: {"user_id": "user123", "content_type": "BOOK", ...}
        3. search_content: {any field combinations without the attributes wrapper}
        4. Legacy format: {"attributes": {field combinations}, ...}
        
        All formats support pagination with:
        - limit: Maximum number of items to return
        - pagination_token: Token for retrieving the next page of results
        
        USER ISOLATION: Automatically filters content by authenticated user's user_id
        unless the user is an admin with explicit override permissions.
        """
        try:
            # Handle different payload formats based on the action that was called
            action = payload.get("__action__", "search_content")
            search_params = {}
            limit = payload.get("limit")
            pagination_token = payload.get("pagination_token") or payload.get("next_token")
            
            # Format 1: list_content_by_publisher
            if action == "list_content_by_user":
                require_keys(payload, ["user_id"])
                search_params = {"user_id": payload["user_id"]}
            
            # Format 2: list_content_by_publisher_and_type
            elif action == "list_content_by_user_and_type":
                require_keys(payload, ["user_id", "content_type"])
                content_type = payload["content_type"]
                
                # Validate content_type parameter
                error = self._validate_content_type({"type": content_type})
                if error:
                    message, code = ResponseFormatter.extract_error_info(error)
                    return ResponseFormatter.format_error(message, ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
                
                search_params = {
                    "user_id": payload["user_id"],
                    "type": content_type
                }
                
            # Format 3: search_content (direct parameters)
            elif action == "search_content":
                # Check for attributes format first (legacy support)
                if "attributes" in payload:
                    attributes = payload.get("attributes")
                    if not isinstance(attributes, dict):
                        return ResponseFormatter.format_error(
                            "The 'attributes' field must be a dictionary of attribute-value pairs",
                            ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"],
                            field="attributes"
                        )
                    search_params = attributes.copy()
                else:
                    # Use all parameters directly as search criteria
                    search_params = payload.copy()
                    # Remove pagination and API processing parameters
                    search_params.pop("limit", None)
                    search_params.pop("pagination_token", None)
                    search_params.pop("__action__", None)
                    # Remove API processing artifacts that shouldn't be used for content searching
                    search_params.pop("_headers", None)
                    search_params.pop("auth_context", None)
                    search_params.pop("userData", None)
            
            # APPLY USER ISOLATION: Automatically filter by authenticated user's publisher_id
            # unless already specified or user is admin with override permissions
            search_params = self._apply_user_isolation(search_params, payload)
            
            # Validate status parameter if provided
            error = self._validate_content_status(search_params)
            if error:
                message, code = ResponseFormatter.extract_error_info(error)
                return ResponseFormatter.format_error(message, ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
                
            # Validate workflow status parameters if provided
            error = self._validate_workflow_status_fields(search_params)
            if error:
                message, code = ResponseFormatter.extract_error_info(error)
                return ResponseFormatter.format_error(message, ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
                    
            # Validate type parameter if provided
            error = self._validate_content_type(search_params)
            if error:
                message, code = ResponseFormatter.extract_error_info(error)
                return ResponseFormatter.format_error(message, ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
            
            # CRITICAL: Extract user_id from auth context for user isolation
            auth_context = AuthContext.from_payload(payload)
            if not auth_context.is_authenticated():
                return ResponseFormatter.format_error(
                    "User authentication required for content search",
                    ResponseFormatter.ERROR_CODES["AUTHENTICATION_ERROR"]
                )
            
            # Execute search with the provided attributes and user_id for user isolation
            search_result = self.helper.search_content(
                search_params=search_params,
                limit=limit,
                pagination_token=pagination_token,
                user_id=auth_context.user_id
            )
            
            # Handle error case
            if "error" in search_result:
                message, code = ResponseFormatter.extract_error_info(search_result)
                return ResponseFormatter.format_error(message, code)
            
            # Extract pagination info
            pagination_info = search_result.get("pagination", {})
            
            # Format standardized list response
            return ResponseFormatter.format_list_response(
                items=search_result.get("items", []),
                count=search_result.get("count", 0),
                total_scanned=search_result.get("total_scanned", 0),
                pagination_token=pagination_info.get("next_token"),
                has_more=pagination_info.get("has_more", False)
            )
        except Exception as e:
            logger.error(f"Error searching content: {str(e)}")
            return ResponseFormatter.format_error(f"Failed to search content: {str(e)}", 
                                               ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])

    def _is_isbn_only_upload(self, payload: Dict) -> bool:
        """
        Check if this is an ISBN-only book upload (only type and isbn provided).
        
        Args:
            payload: Request payload dictionary
            
        Returns:
            True if this is an ISBN-only upload, False otherwise
        """
        # Required fields for ISBN-only upload
        has_isbn = "isbn" in payload and payload["isbn"]
        
        # Fields that indicate full manual entry (not ISBN-only)
        manual_fields = ["title", "authors", "year", "keywords"]
        has_manual_fields = any(field in payload for field in manual_fields)
        
        # It's ISBN-only if we have ISBN but no manual fields
        return has_isbn and not has_manual_fields
    
    def _enrich_book_from_isbn(self, payload: Dict) -> Dict:
        """
        Enrich book payload by fetching details from Google Books API using ISBN.
        
        Args:
            payload: Original payload with ISBN
            
        Returns:
            Enriched payload with book details or error payload if enrichment fails
        """
        isbn = payload.get("isbn")
        if not isbn:
            return {"error": "ISBN is required for book enrichment"}
        
        logger.info(f"Enriching book data for ISBN: {isbn}")
        
        try:
            # Get book details from Google Books API
            google_book_data = self.google_books_helper.get_book_details(isbn)
            
            # Check if Google Books API returned an error
            if "error" in google_book_data:
                logger.warning(f"Google Books API error for ISBN {isbn}: {google_book_data['error']}")
                return {"error": f"Failed to fetch book details from Google Books: {google_book_data['error']}"}
            
            # Map Google Books fields to our BookContent model fields
            enriched_payload = payload.copy()
            
            # Core book information
            if google_book_data.get("title"):
                enriched_payload["title"] = google_book_data["title"]
            
            if google_book_data.get("authors"):
                enriched_payload["authors"] = google_book_data["authors"]
            
            # Add publisher information
            if google_book_data.get("publisher"):
                enriched_payload["publisher"] = google_book_data["publisher"]
            
            # Extract year from publishedDate (e.g., "2007-03-28" -> "2007")  
            if google_book_data.get("publishedDate"):
                published_date = google_book_data["publishedDate"]
                try:
                    # Extract year from various date formats
                    if "-" in published_date:
                        year = published_date.split("-")[0]
                    else:
                        year = published_date[:4]  # Take first 4 characters as year
                    enriched_payload["year"] = year
                except (ValueError, IndexError):
                    logger.warning(f"Could not parse year from publishedDate: {published_date}")
            
            # Create keywords from categories and description
            keywords = []
            
            # Add categories as keywords
            if google_book_data.get("categories"):
                keywords.extend(google_book_data["categories"])
            
            # Extract keywords from description (simple approach - take meaningful words)
            if google_book_data.get("description"):
                description = google_book_data["description"]
                # Extract some meaningful keywords from description
                # This is a simple implementation - could be enhanced with NLP
                description_words = description.lower().split()
                meaningful_words = [
                    word.strip(".,!?;:\"'()[]{}") 
                    for word in description_words 
                    if len(word) > 4 and word.isalpha()
                ]
                # Take first few meaningful words to avoid too many keywords
                keywords.extend(meaningful_words[:5])
            
            # Remove duplicates and empty values
            keywords = list(set(filter(None, keywords)))
            if keywords:
                enriched_payload["keywords"] = keywords
            
            # Extract image URLs from imageLinks
            image_links = google_book_data.get("imageLinks", {})
            if image_links.get("thumbnail"):
                enriched_payload["thumbnail_url"] = image_links["thumbnail"]
            if image_links.get("smallThumbnail"):
                enriched_payload["small_thumbnail_url"] = image_links["smallThumbnail"]
            
            # Ensure ISBN is preserved
            enriched_payload["isbn"] = isbn
            
            # Set default workflow statuses if not provided
            if "rag_status" not in enriched_payload:
                enriched_payload["rag_status"] = "DISABLED"
            if "training_status" not in enriched_payload:
                enriched_payload["training_status"] = "DISABLED"
            if "licensing_status" not in enriched_payload:
                enriched_payload["licensing_status"] = "DISABLED"
            
            logger.info(f"Successfully enriched book data for ISBN {isbn}: {enriched_payload.get('title', 'Unknown Title')}")
            return enriched_payload
            
        except Exception as e:
            logger.error(f"Error enriching book data for ISBN {isbn}: {str(e)}")
            return {"error": f"Failed to enrich book data: {str(e)}"}

    def _process_auth_context_safely(self, auth_context: Any) -> Dict:
        """
        Process auth_context to ensure it's properly formatted as a dictionary
        with type-safe handling of the cognito:groups field.
        
        Args:
            auth_context: The auth_context value (could be string, dict, or other)
            
        Returns:
            Safely processed auth_context as a dictionary
        """
        try:
            # Use DataTypeUtils to safely process auth_context
            processed_context = DataTypeUtils.safe_dict_conversion(auth_context)
            
            # Special handling for cognito:groups field if present
            if "cognito:groups" in processed_context:
                groups_value = processed_context["cognito:groups"]
                processed_context["cognito:groups"] = DataTypeUtils.safe_list_conversion(groups_value)
            
            return processed_context
            
        except Exception as e:
            logger.error(f"Error processing auth_context safely: {str(e)}")
            # Return minimal safe auth_context on error
            return {}

    def _apply_user_isolation(self, search_params: Dict, payload: Dict) -> Dict:
        """
        Apply user isolation by automatically filtering content by authenticated user's user_id
        unless already specified or user is admin with override permissions.
        
        Args:
            search_params: Original search parameters
            payload: Original payload containing auth context
            
        Returns:
            Updated search parameters with user isolation applied
        """
        try:
            # Get authenticated user context
            auth_context = AuthContext.from_payload(payload)
            
            # If user is not authenticated, don't apply isolation (will be handled by auth middleware)
            if not auth_context.is_authenticated():
                logger.warning("User isolation: No authenticated user found, returning original params")
                return search_params
            
            # If user_id is already specified in search params, respect the existing value
            # This allows admin users to search specific users if they have explicit user_id
            if "user_id" in search_params:
                logger.info(f"User isolation: user_id already specified ({search_params['user_id']}), using existing value")
                return search_params
            
            # For admin users, check if they have an explicit bypass flag
            # This allows admins to see all content when specifically requested
            if auth_context.role == "ADMIN" and payload.get("bypass_user_isolation", False):
                logger.info(f"User isolation: Admin user {auth_context.user_id} bypassing user isolation")
                return search_params
            
            # Apply user isolation: automatically filter by authenticated user's user_id
            search_params = search_params.copy()
            search_params["user_id"] = auth_context.user_id
            
            logger.info(f"User isolation: Applied user_id filter for user {auth_context.user_id} ({auth_context.role})")
            return search_params
            
        except Exception as e:
            logger.error(f"Error applying user isolation: {str(e)}")
            # On error, return original params to avoid breaking the system
            return search_params

    def _get_content_count(self, payload: Dict) -> Dict:
        """
        Get content count for authenticated user by reusing existing search logic with count_only=True.
        Supports all content types (BOOK, AUDIO, VIDEO, etc.) and all search filters.
        
        USER ISOLATION: Automatically filters content by authenticated user's publisher_id
        unless the user is an admin with explicit override permissions.
        
        Optional payload keys:
        - type: Content type (BOOK, AUDIO, etc.)
        - status: Content status (ACTIVE, ARCHIVED, etc.)
        - rag_status: RAG workflow status (ENABLED, DISABLED)
        - training_status: Training workflow status (ENABLED, DISABLED)
        - licensing_status: Licensing workflow status (ENABLED, DISABLED)
        - publisher_id: Publisher ID (for filtering by publisher)
        - Any other search parameters supported by search_content
        
        Returns:
            Dict with count information and total_scanned metadata
        """
        try:
            # Use the same search parameter processing as search_content
            search_params = payload.copy()
            
            # Remove pagination and API processing parameters
            search_params.pop("limit", None)
            search_params.pop("pagination_token", None)
            search_params.pop("__action__", None)
            # Remove API processing artifacts that shouldn't be used for content searching
            search_params.pop("_headers", None)
            search_params.pop("auth_context", None)
            search_params.pop("userData", None)
            
            # Handle legacy attributes format
            if "attributes" in payload:
                attributes = payload.get("attributes")
                if not isinstance(attributes, dict):
                    return ResponseFormatter.format_error(
                        "The 'attributes' field must be a dictionary of attribute-value pairs",
                        ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"],
                        field="attributes"
                    )
                search_params = attributes.copy()
            
            # APPLY USER ISOLATION: Automatically filter by authenticated user's publisher_id
            # unless already specified or user is admin with override permissions
            search_params = self._apply_user_isolation(search_params, payload)
            
            # Validate status parameter if provided
            error = self._validate_content_status(search_params)
            if error:
                message, code = ResponseFormatter.extract_error_info(error)
                return ResponseFormatter.format_error(message, ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
                
            # Validate workflow status parameters if provided
            error = self._validate_workflow_status_fields(search_params)
            if error:
                message, code = ResponseFormatter.extract_error_info(error)
                return ResponseFormatter.format_error(message, ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
                    
            # Validate type parameter if provided
            error = self._validate_content_type(search_params)
            if error:
                message, code = ResponseFormatter.extract_error_info(error)
                return ResponseFormatter.format_error(message, ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
            
            # CRITICAL: Extract user_id from auth context for user isolation
            auth_context = AuthContext.from_payload(payload)
            if not auth_context.is_authenticated():
                return ResponseFormatter.format_error(
                    "User authentication required for content count",
                    ResponseFormatter.ERROR_CODES["AUTHENTICATION_ERROR"]
                )
            
            # Execute search with count_only=True and user_id for user isolation
            count_result = self.helper.search_content(
                search_params=search_params,
                count_only=True,
                user_id=auth_context.user_id
            )
            
            # Handle error case
            if "error" in count_result:
                message, code = ResponseFormatter.extract_error_info(count_result)
                return ResponseFormatter.format_error(message, code)
            
            # Format successful count response
            return ResponseFormatter.format_success({
                "count": count_result.get("count", 0),
                "total_scanned": count_result.get("total_scanned", 0)
            })
            
        except Exception as e:
            logger.error(f"Error getting content count: {str(e)}")
            return ResponseFormatter.format_error(f"Failed to get content count: {str(e)}", 
                                               ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])
