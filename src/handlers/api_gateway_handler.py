"""
API Gateway Lambda handler for Knowlio REST API.
Transforms API Gateway events into processor events and handles HTTP responses.
"""

import json
import traceback
from typing import Any, Dict, Optional

from exceptions.processor_exceptions.exceptions import ProcessorNotFoundError, InvalidInputError, \
    ProcessorExecutionError
from helpers.common_helper.logger_helper import LoggerHelper
from config.api_routes import KnowlioApiRoutes, ApiRoute
from sync_processor_registry.bootstrap import load_all_processors
from sync_processor_registry.processor_registry import ProcessorRegistry

logger = LoggerHelper(__name__).get_logger()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for API Gateway events.
    Transforms REST API calls into processor events.
    """
    logger.info("Received API Gateway event: %s", json.dumps(event, default=str))

    try:
        # Load all processors
        load_all_processors()
        
        # Check if this is an API Gateway event
        if _is_api_gateway_event(event):
            return _handle_api_gateway_event(event, context)
        else:
            # Fallback to direct processor event (for backwards compatibility)
            return _handle_direct_processor_event(event, context)

    except ProcessorNotFoundError as e:
        logger.warning("Processor not found: %s", str(e))
        return _http_response(404, {"error": "Processor not found", "message": str(e)})

    except InvalidInputError as e:
        logger.warning("Invalid input: %s", str(e))
        return _http_response(400, {"error": "Invalid input", "message": str(e)})

    except ProcessorExecutionError as e:
        logger.error("Processor execution failed: %s", str(e))
        return _http_response(500, {"error": "Processor execution failed", "message": str(e)})

    except Exception as e:
        logger.exception("Unexpected error occurred: %s", str(e))
        return _http_response(500, {"error": "Internal server error", "message": "An unexpected error occurred"})


def _is_api_gateway_event(event: Dict[str, Any]) -> bool:
    """Check if the event is from API Gateway"""
    return "httpMethod" in event and "path" in event


def _handle_api_gateway_event(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle API Gateway proxy integration event"""
    
    # Extract HTTP method and path
    http_method = event.get("httpMethod", "").upper()
    path = event.get("path", "").lstrip("/")  # Remove leading slash
    
    logger.info("Processing API Gateway request: %s %s", http_method, path)
    
    # Find matching route
    route = _find_matching_route(http_method, path)
    if not route:
        return _http_response(404, {"error": "Route not found", "message": f"No route found for {http_method} /{path}"})
    
    # Extract and build payload
    payload = _build_payload_from_api_gateway_event(event, route)
    
    # Execute processor
    processor = _resolve_processor(route.processor_name)
    result = _execute_processor(processor, route.action, payload)
    
    return _http_response(200, result)


def _handle_direct_processor_event(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle direct processor event (backwards compatibility)"""
    processor_name = event.get("processor_name")
    action = event.get("action")
    payload = event.get("payload", {})
    
    if not processor_name or not action:
        return _http_response(400, {"error": "Missing required fields", "message": "processor_name and action are required"})
    
    processor = _resolve_processor(processor_name)
    result = _execute_processor(processor, action, payload)
    
    return _http_response(200, result)


def _find_matching_route(http_method: str, path: str) -> Optional[ApiRoute]:
    """Find a matching route configuration for the given HTTP method and path"""
    
    # First try exact match
    for route in KnowlioApiRoutes.get_all_routes():
        if route.method == http_method and route.path == path:
            return route
    
    # Then try path parameter matching
    for route in KnowlioApiRoutes.get_all_routes():
        if route.method == http_method and _path_matches_with_parameters(route.path, path):
            return route
    
    return None


def _path_matches_with_parameters(route_path: str, request_path: str) -> bool:
    """Check if a route path matches a request path, considering path parameters"""
    route_segments = route_path.split('/')
    request_segments = request_path.split('/')
    
    if len(route_segments) != len(request_segments):
        return False
    
    for route_seg, request_seg in zip(route_segments, request_segments):
        # If route segment is a parameter (contains {}), it matches any value
        if not (route_seg.startswith('{') and route_seg.endswith('}')) and route_seg != request_seg:
            return False
    
    return True


def _build_payload_from_api_gateway_event(event: Dict[str, Any], route: ApiRoute) -> Dict[str, Any]:
    """Build processor payload from API Gateway event"""
    payload = {}
    
    # Add path parameters
    if route.path_parameters:
        path_params = event.get("pathParameters") or {}
        payload.update(path_params)
    
    # Add query parameters
    if route.query_parameters:
        query_params = event.get("queryStringParameters") or {}
        payload.update(query_params)
    
    # Add body content for POST/PUT requests
    if event.get("httpMethod") in ["POST", "PUT", "PATCH"]:
        body = event.get("body")
        if body:
            try:
                body_data = json.loads(body)
                if isinstance(body_data, dict):
                    payload.update(body_data)
            except json.JSONDecodeError:
                logger.warning("Failed to parse request body as JSON")
    
    # Add headers if needed (can be used for authentication, etc.)
    headers = event.get("headers") or {}
    if headers:
        payload["_headers"] = headers
    
    logger.info("Built payload for processor: %s", json.dumps(payload, default=str))
    return payload


def _resolve_processor(processor_name: str):
    """Resolve processor class from registry"""
    try:
        processor = ProcessorRegistry.get_processor(processor_name)
        logger.info("Resolved processor: %s", processor_name)
        return processor
    except ValueError as e:
        raise ProcessorNotFoundError(str(e))


def _execute_processor(processor_class, action: str, payload: Dict[str, Any]) -> Any:
    """Execute processor with the given action and payload"""
    try:
        logger.info("Executing processor with action: %s, payload: %s", action, json.dumps(payload, default=str))
        processor_instance = processor_class()
        return processor_instance.process(action, payload)
    except Exception as e:
        logger.error("Processor execution failed: %s", str(e))
        logger.error("Traceback:\n%s", traceback.format_exc())
        raise ProcessorExecutionError("Processor execution failed due to an unexpected error.")


def _http_response(status_code: int, body: Any) -> Dict[str, Any]:
    """Create HTTP response with CORS headers"""
    response = {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
        },
        "body": json.dumps(body, default=str)
    }
    
    logger.info("Returning HTTP response: %s", json.dumps(response, default=str))
    return response
