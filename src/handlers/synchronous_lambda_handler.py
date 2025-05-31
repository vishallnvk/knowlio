import json
import traceback
from typing import Any, Dict

from exceptions.processor_exceptions.exceptions import ProcessorNotFoundError, InvalidInputError, \
    ProcessorExecutionError
from helpers.common_helper.logger_helper import LoggerHelper
from models.event_input import ProcessorEventInput
from sync_processor_registry.bootstrap import load_all_processors
from sync_processor_registry.processor_registry import ProcessorRegistry

logger = LoggerHelper(__name__).get_logger()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logger.info("Received event: %s", json.dumps(event))

    try:
        load_all_processors()
        processor_name, payload = _parse_event(event)
        processor = _resolve_processor(processor_name)
        result = _execute_processor(processor, payload)
        return _response(200, result)

    except ProcessorNotFoundError as e:
        logger.warning("Processor not found: %s", str(e))
        return _response(404, str(e))

    except InvalidInputError as e:
        logger.warning("Invalid input: %s", str(e))
        return _response(400, str(e))

    except ProcessorExecutionError as e:
        logger.error("Processor execution failed: %s", str(e))
        return _response(500, str(e))

    except Exception as e:
        logger.exception("Unexpected error occurred: %s", str(e))
        return _response(500, "Internal server error")


def _parse_event(event: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    try:
        parsed_input = ProcessorEventInput(event)
        return parsed_input.processor_name, parsed_input.payload
    except ValueError as e:
        raise InvalidInputError(f"Validation failed: {str(e)}")


def _resolve_processor(processor_name: str):
    try:
        processor = ProcessorRegistry.get_processor(processor_name)
        logger.info("Resolved processor: %s", processor_name)
        return processor
    except ValueError as e:
        raise ProcessorNotFoundError(str(e))


def _execute_processor(processor_class, payload: Dict[str, Any]) -> Any:
    try:
        logger.info("Executing processor with payload: %s", json.dumps(payload, default=str))
        processor_instance = processor_class()
        return processor_instance.process(payload)
    except Exception as e:
        logger.error("Processor execution failed: %s", str(e))
        logger.error("Traceback:\n%s", traceback.format_exc())
        raise ProcessorExecutionError("Processor execution failed due to an unexpected error.")


def _response(status_code: int, body: Any) -> Dict[str, Any]:
    response = {"statusCode": status_code, "body": json.dumps(body, default=str)}
    logger.info("Returning response: %s", json.dumps(response, default=str))
    return response