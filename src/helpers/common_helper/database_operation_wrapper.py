"""
Database Operation Wrapper - Universal Type-Safe Database Operations
Provides type-safe database operations across all applications
"""

import json
from typing import Dict, List, Any, Optional, Union
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.common_helper.data_type_utils import DataTypeUtils

logger = LoggerHelper(__name__).get_logger()


class DatabaseOperationWrapper:
    """
    Universal wrapper for all database operations to ensure type safety
    across the entire application ecosystem.
    """
    
    @staticmethod
    def sanitize_for_database(data: Any) -> Any:
        """
        Sanitize data for database operations, ensuring all types are compatible.
        
        Args:
            data: Input data of any type
            
        Returns:
            Sanitized data safe for database operations
        """
        try:
            if data is None:
                return None
            
            # Handle dictionaries recursively
            if isinstance(data, dict):
                sanitized = {}
                for key, value in data.items():
                    # Ensure key is always a string
                    safe_key = DataTypeUtils.safe_string_conversion(key)
                    sanitized[safe_key] = DatabaseOperationWrapper.sanitize_for_database(value)
                return sanitized
            
            # Handle lists recursively
            elif isinstance(data, list):
                return [DatabaseOperationWrapper.sanitize_for_database(item) for item in data]
            
            # Handle strings
            elif isinstance(data, str):
                return data
            
            # Handle numbers
            elif isinstance(data, (int, float)):
                return data
            
            # Handle booleans
            elif isinstance(data, bool):
                return data
            
            # Handle complex types by converting to string
            else:
                return DataTypeUtils.safe_string_conversion(data)
                
        except Exception as e:
            logger.warning(f"Error sanitizing data for database: {str(e)}")
            return DataTypeUtils.safe_string_conversion(data)
    
    @staticmethod
    def prepare_update_expression(updates: Dict[str, Any]) -> tuple:
        """
        Prepare a safe update expression for DynamoDB operations.
        
        Args:
            updates: Dictionary of updates to apply
            
        Returns:
            Tuple of (update_expression, expression_attr_names, expression_attr_values)
        """
        try:
            if not updates:
                return None, None, None
            
            # Sanitize all updates
            sanitized_updates = DatabaseOperationWrapper.sanitize_for_database(updates)
            
            # Build safe update expression
            update_parts = []
            expression_attr_names = {}
            expression_attr_values = {}
            
            for key, value in sanitized_updates.items():
                # Ensure key is a valid string
                safe_key = DataTypeUtils.safe_string_conversion(key)
                
                # Create safe attribute name reference
                attr_name = f"#{safe_key}"
                attr_value = f":{safe_key}"
                
                update_parts.append(f"{attr_name}={attr_value}")
                expression_attr_names[attr_name] = safe_key
                expression_attr_values[attr_value] = value
            
            update_expression = "SET " + ", ".join(update_parts)
            
            logger.debug(f"Prepared update expression: {update_expression}")
            return update_expression, expression_attr_names, expression_attr_values
            
        except Exception as e:
            logger.error(f"Error preparing update expression: {str(e)}")
            # Return safe defaults
            return None, None, None
    
    @staticmethod
    def safe_item_conversion(item: Any) -> Dict[str, Any]:
        """
        Safely convert any item to a dictionary suitable for database operations.
        
        Args:
            item: Item to convert
            
        Returns:
            Safe dictionary representation
        """
        try:
            if item is None:
                return {}
            
            if isinstance(item, dict):
                return DatabaseOperationWrapper.sanitize_for_database(item)
            
            # Try to convert to dict if it has a to_dict method
            if hasattr(item, 'to_dict') and callable(getattr(item, 'to_dict')):
                return DatabaseOperationWrapper.sanitize_for_database(item.to_dict())
            
            # Try to convert to dict if it has __dict__
            if hasattr(item, '__dict__'):
                return DatabaseOperationWrapper.sanitize_for_database(item.__dict__)
            
            # For other types, create a simple dictionary
            return {"value": DataTypeUtils.safe_string_conversion(item)}
            
        except Exception as e:
            logger.error(f"Error converting item to dict: {str(e)}")
            return {"error": "conversion_failed", "original_type": str(type(item))}
    
    @staticmethod
    def safe_key_conversion(key: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Safely convert a key for database operations.
        
        Args:
            key: Key to convert (string or dict)
            
        Returns:
            Safe key dictionary
        """
        try:
            if isinstance(key, str):
                return {"id": key}
            elif isinstance(key, dict):
                return DatabaseOperationWrapper.sanitize_for_database(key)
            else:
                return {"id": DataTypeUtils.safe_string_conversion(key)}
                
        except Exception as e:
            logger.error(f"Error converting key: {str(e)}")
            return {"id": "unknown"}
    
    @staticmethod
    def validate_database_operation(operation_name: str, **kwargs) -> bool:
        """
        Validate database operation parameters before execution.
        
        Args:
            operation_name: Name of the operation
            **kwargs: Operation parameters
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            logger.debug(f"Validating {operation_name} operation")
            
            # Check for required parameters based on operation type
            if operation_name == "put_item":
                return "item" in kwargs and kwargs["item"] is not None
            
            elif operation_name == "get_item":
                return "key" in kwargs and kwargs["key"] is not None
            
            elif operation_name == "update_item":
                return all(param in kwargs for param in ["key", "updates"]) and \
                       kwargs["key"] is not None and kwargs["updates"] is not None
            
            elif operation_name in ["query_items", "scan_items"]:
                return True  # These operations have optional parameters
            
            else:
                logger.warning(f"Unknown operation: {operation_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error validating {operation_name} operation: {str(e)}")
            return False
    
    @staticmethod
    def log_operation_safely(operation_name: str, **kwargs):
        """
        Safely log database operations without causing type errors.
        
        Args:
            operation_name: Name of the operation
            **kwargs: Operation parameters
        """
        try:
            safe_kwargs = {}
            for key, value in kwargs.items():
                safe_kwargs[key] = DataTypeUtils.safe_logging_format(value)
            
            logger.info(f"Database operation: {operation_name} with params: {safe_kwargs}")
            
        except Exception as e:
            logger.warning(f"Error logging operation {operation_name}: {str(e)}")
            logger.info(f"Database operation: {operation_name} (logging details failed)")
    
    @staticmethod
    def safe_process_payload(payload: Any) -> Dict[str, Any]:
        """
        Safely process an entire payload dictionary to ensure type safety.
        
        This method processes all fields in a payload through type-safe conversion,
        ensuring that complex data structures are properly handled and won't cause
        type errors in subsequent operations.
        
        Args:
            payload: Input payload of any type (typically a dictionary)
            
        Returns:
            Type-safe payload dictionary suitable for database operations
        """
        try:
            if payload is None:
                return {}
            
            # If payload is already a dict, process it recursively
            if isinstance(payload, dict):
                return DatabaseOperationWrapper.sanitize_for_database(payload)
            
            # If payload is a string, try to parse it as JSON
            if isinstance(payload, str):
                try:
                    parsed_payload = json.loads(payload)
                    return DatabaseOperationWrapper.sanitize_for_database(parsed_payload)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse payload as JSON: {payload}")
                    return {"raw_payload": payload}
            
            # For other types, try to convert to dict if possible
            if hasattr(payload, 'to_dict') and callable(getattr(payload, 'to_dict')):
                return DatabaseOperationWrapper.sanitize_for_database(payload.to_dict())
            
            # If payload has __dict__, use it
            if hasattr(payload, '__dict__'):
                return DatabaseOperationWrapper.sanitize_for_database(payload.__dict__)
            
            # For primitive types, wrap in a dictionary
            return {"value": DatabaseOperationWrapper.sanitize_for_database(payload)}
            
        except Exception as e:
            logger.error(f"Error processing payload safely: {str(e)}")
            # Return a minimal safe payload on error
            return {
                "error": "payload_processing_failed",
                "original_type": str(type(payload)),
                "error_message": str(e)
            }
