"""
Data Type Utilities for handling mixed data types safely.

This module provides utilities for safely handling data type conversions and validations,
particularly for cases where data might contain mixed types (strings, lists, dicts, etc.).
"""

from typing import Any, List, Dict, Union, Optional
import json
from helpers.common_helper.logger_helper import LoggerHelper

logger = LoggerHelper(__name__).get_logger()


class DataTypeUtils:
    """Utilities for safe data type handling and conversions."""
    
    @staticmethod
    def safe_string_conversion(value: Any) -> str:
        """
        Safely convert any value to a string representation.
        
        Args:
            value: Any value to convert to string
            
        Returns:
            String representation of the value
        """
        if value is None:
            return ""
        elif isinstance(value, str):
            return value
        elif isinstance(value, (int, float, bool)):
            return str(value)
        elif isinstance(value, list):
            # Convert list to comma-separated string, handling nested structures
            try:
                safe_items = []
                for item in value:
                    if isinstance(item, list):
                        # Handle nested lists by converting them to bracketed strings
                        nested_items = [str(sub_item) for sub_item in item]
                        safe_items.append("[" + ", ".join(nested_items) + "]")
                    elif isinstance(item, dict):
                        # Handle nested dicts
                        try:
                            safe_items.append(json.dumps(item, default=str))
                        except (TypeError, ValueError):
                            safe_items.append(str(item))
                    else:
                        safe_items.append(str(item))
                return ", ".join(safe_items)
            except Exception as e:
                logger.warning(f"Error in safe_string_conversion for list: {str(e)}")
                return str(value)
        elif isinstance(value, dict):
            # Convert dict to JSON string
            try:
                return json.dumps(value, default=str)
            except (TypeError, ValueError):
                return str(value)
        else:
            return str(value)
    
    @staticmethod
    def safe_list_conversion(value: Any) -> List[str]:
        """
        Safely convert any value to a list of strings.
        
        Args:
            value: Any value to convert to list of strings
            
        Returns:
            List of strings
        """
        if value is None:
            return []
        elif isinstance(value, str):
            # Handle comma-separated strings
            if "," in value:
                return [item.strip() for item in value.split(",")]
            else:
                return [value]
        elif isinstance(value, list):
            # Convert all items to strings
            return [DataTypeUtils.safe_string_conversion(item) for item in value]
        else:
            return [DataTypeUtils.safe_string_conversion(value)]
    
    @staticmethod
    def normalize_search_value(value: Any) -> Any:
        """
        Normalize a search value to handle common data type issues.
        
        Args:
            value: Value to normalize
            
        Returns:
            Normalized value suitable for searching
        """
        if value is None:
            return ""
        elif isinstance(value, str):
            return value.strip()
        elif isinstance(value, (int, float, bool)):
            return value
        elif isinstance(value, list):
            # If it's a list of strings, return as is
            # If it contains non-strings, convert them
            return [DataTypeUtils.safe_string_conversion(item) if not isinstance(item, str) else item for item in value]
        else:
            return DataTypeUtils.safe_string_conversion(value)
    
    @staticmethod
    def safe_contains_check(container: Any, search_value: Any) -> bool:
        """
        Safely check if a container contains a search value.
        
        Args:
            container: Container to search in (string, list, etc.)
            search_value: Value to search for
            
        Returns:
            True if container contains search_value, False otherwise
        """
        try:
            if container is None or search_value is None:
                return False
            
            # Convert both to strings for comparison
            container_str = DataTypeUtils.safe_string_conversion(container).lower()
            search_str = DataTypeUtils.safe_string_conversion(search_value).lower()
            
            return search_str in container_str
            
        except Exception as e:
            logger.warning(f"Error in safe_contains_check: {str(e)}")
            return False
    
    @staticmethod
    def safe_equality_check(value1: Any, value2: Any) -> bool:
        """
        Safely check if two values are equal, handling type mismatches.
        
        Args:
            value1: First value
            value2: Second value
            
        Returns:
            True if values are equal, False otherwise
        """
        try:
            # Handle None values
            if value1 is None and value2 is None:
                return True
            if value1 is None or value2 is None:
                return False
            
            # If both are same type, use direct comparison
            if type(value1) == type(value2):
                return value1 == value2
            
            # Convert both to strings for comparison
            str1 = DataTypeUtils.safe_string_conversion(value1).lower()
            str2 = DataTypeUtils.safe_string_conversion(value2).lower()
            
            return str1 == str2
            
        except Exception as e:
            logger.warning(f"Error in safe_equality_check: {str(e)}")
            return False
    
    @staticmethod
    def validate_and_fix_data_types(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and fix data types in a dictionary to prevent type-related errors.
        
        Args:
            data: Dictionary to validate and fix
            
        Returns:
            Dictionary with corrected data types
        """
        if not isinstance(data, dict):
            logger.warning("validate_and_fix_data_types: Input is not a dictionary")
            return {}
        
        fixed_data = {}
        
        for key, value in data.items():
            try:
                # Ensure key is a string
                key_str = DataTypeUtils.safe_string_conversion(key)
                
                # Handle different value types
                if isinstance(value, dict):
                    # Recursively fix nested dictionaries
                    fixed_data[key_str] = DataTypeUtils.validate_and_fix_data_types(value)
                elif isinstance(value, list):
                    # Ensure all list items are properly typed
                    fixed_list = []
                    for item in value:
                        if isinstance(item, dict):
                            fixed_list.append(DataTypeUtils.validate_and_fix_data_types(item))
                        else:
                            fixed_list.append(item)
                    fixed_data[key_str] = fixed_list
                else:
                    # Keep the original value for other types
                    fixed_data[key_str] = value
                    
            except Exception as e:
                logger.warning(f"Error fixing data type for key '{key}': {str(e)}")
                # In case of error, convert to string
                fixed_data[DataTypeUtils.safe_string_conversion(key)] = DataTypeUtils.safe_string_conversion(value)
        
        return fixed_data
    
    @staticmethod
    def safe_logging_format(value: Any) -> str:
        """
        Format a value safely for logging to prevent logging-related errors.
        
        Args:
            value: Value to format for logging
            
        Returns:
            String safe for logging
        """
        try:
            if value is None:
                return "None"
            elif isinstance(value, str):
                # Truncate very long strings for logging
                if len(value) > 500:
                    return value[:497] + "..."
                return value
            elif isinstance(value, (int, float, bool)):
                return str(value)
            elif isinstance(value, list):
                # Format lists safely
                if len(value) > 10:
                    formatted_items = [DataTypeUtils.safe_logging_format(item) for item in value[:10]]
                    return f"[{', '.join(formatted_items)}, ...({len(value)-10} more)]"
                else:
                    formatted_items = [DataTypeUtils.safe_logging_format(item) for item in value]
                    return f"[{', '.join(formatted_items)}]"
            elif isinstance(value, dict):
                # Format dicts safely
                if len(value) > 5:
                    sample_keys = list(value.keys())[:5]
                    formatted_items = [f"{key}: {DataTypeUtils.safe_logging_format(value[key])}" for key in sample_keys]
                    return f"{{{', '.join(formatted_items)}, ...({len(value)-5} more)}}"
                else:
                    formatted_items = [f"{key}: {DataTypeUtils.safe_logging_format(val)}" for key, val in value.items()]
                    return f"{{{', '.join(formatted_items)}}}"
            else:
                # For other types, convert to string but limit length
                str_value = str(value)
                if len(str_value) > 200:
                    return str_value[:197] + "..."
                return str_value
                
        except Exception as e:
            return f"<Error formatting value: {str(e)}>"


class ContentDataValidator:
    """Specialized validator for content data to prevent type-related errors."""
    
    @staticmethod
    def validate_content_attribute_value(attribute: str, value: Any) -> Any:
        """
        Validate and normalize a content attribute value.
        
        Args:
            attribute: Name of the attribute
            value: Value to validate
            
        Returns:
            Validated and normalized value
            
        Raises:
            ValueError: If value is invalid for the attribute
        """
        # List of attributes that should be lists
        list_attributes = ['authors', 'keywords', 'tags', 'categories']
        
        # List of attributes that should be strings
        string_attributes = ['title', 'publisher', 'isbn', 'content_id', 'publisher_id', 'type', 'status', 
                           'licensing_status', 'rag_status', 'training_status']
        
        # List of attributes that should be numbers
        number_attributes = ['year', 'page_count', 'rating']
        
        try:
            if attribute in list_attributes:
                # Ensure value is a list of strings
                return DataTypeUtils.safe_list_conversion(value)
            elif attribute in string_attributes:
                # Ensure value is a string
                return DataTypeUtils.safe_string_conversion(value)
            elif attribute in number_attributes:
                # Ensure value is a number
                if isinstance(value, (int, float)):
                    return value
                elif isinstance(value, str):
                    try:
                        return int(value) if value.isdigit() else float(value)
                    except ValueError:
                        raise ValueError(f"Invalid number format for attribute '{attribute}': {value}")
                else:
                    raise ValueError(f"Invalid type for numeric attribute '{attribute}': {type(value)}")
            else:
                # For other attributes, normalize the value
                return DataTypeUtils.normalize_search_value(value)
                
        except Exception as e:
            logger.error(f"Error validating attribute '{attribute}' with value '{value}': {str(e)}")
            raise ValueError(f"Invalid value for attribute '{attribute}': {str(e)}")
    
    @staticmethod
    def validate_search_parameters(search_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize search parameters to prevent type-related errors.
        
        Args:
            search_params: Search parameters to validate
            
        Returns:
            Validated and normalized search parameters
        """
        validated_params = {}
        
        for key, value in search_params.items():
            try:
                # Validate the key
                key_str = DataTypeUtils.safe_string_conversion(key)
                
                # Validate the value based on the attribute
                validated_value = ContentDataValidator.validate_content_attribute_value(key_str, value)
                validated_params[key_str] = validated_value
                
            except Exception as e:
                logger.warning(f"Error validating search parameter '{key}': {str(e)}")
                # In case of error, use safe conversion
                validated_params[DataTypeUtils.safe_string_conversion(key)] = DataTypeUtils.normalize_search_value(value)
        
        return validated_params
