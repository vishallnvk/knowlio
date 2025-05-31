"""
Registry to register and retrieve processor functions by name.
Enables dynamic processor resolution at runtime.
"""

from typing import Callable, Dict

from helpers.common_helper.logger_helper import LoggerHelper

logger = LoggerHelper(__name__).get_logger()


class ProcessorRegistry:
    _registry: Dict[str, Callable] = {}

    @classmethod
    def register(cls, name: str):
        def decorator(func: Callable):
            cls._registry[name] = func
            return func

        return decorator

    @classmethod
    def get_processor(cls, name: str) -> Callable:
        if name not in cls._registry:
            raise ValueError(f"Processor '{name}' not registered.")
        return cls._registry[name]
