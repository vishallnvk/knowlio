import functools
import time
import logging
from typing import Dict, Callable, Any, Type, List, Union, Optional

def require_keys(payload: Dict, keys: list):
    missing = [k for k in keys if k not in payload]
    if missing:
        raise ValueError(f"Missing required keys: {', '.join(missing)}")

class Retry:
    """
    A decorator for retrying functions that may fail due to transient errors.
    Particularly useful for AWS service calls, external API requests, and other network operations.
    
    Args:
        max_attempts: Maximum number of attempts to make (default: 3)
        initial_wait: Initial wait time in seconds between retries (default: 1)
        backoff_factor: Multiplier for wait time after each retry (default: 2)
        exceptions: List of exception types to catch and retry (default: Exception)
        
    Example usage:
    ```
    @Retry(max_attempts=3, initial_wait=1)
    def call_external_service(params):
        # This function will be retried up to 3 times if it fails
        return aws_service.call(params)
    ```
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_wait: float = 1.0,
        backoff_factor: float = 2.0,
        exceptions: Union[Type[Exception], List[Type[Exception]]] = Exception,
    ):
        self.max_attempts = max_attempts
        self.initial_wait = initial_wait
        self.backoff_factor = backoff_factor
        
        # Ensure exceptions is a tuple (required for except clause)
        if isinstance(exceptions, list):
            self.exceptions = tuple(exceptions)
        elif isinstance(exceptions, type) and issubclass(exceptions, Exception):
            self.exceptions = (exceptions,)
        else:
            self.exceptions = (Exception,)
            
        # Set up logging
        self.logger = logging.getLogger("retry")
    
    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempts = 0
            wait_time = self.initial_wait
            
            while True:
                attempts += 1
                try:
                    return func(*args, **kwargs)
                except self.exceptions as e:
                    if attempts >= self.max_attempts:
                        self.logger.error(
                            f"Function {func.__name__} failed after {attempts} attempts. "
                            f"Last error: {str(e)}"
                        )
                        raise  # Re-raise the last exception when max attempts reached
                    
                    self.logger.warning(
                        f"Attempt {attempts}/{self.max_attempts} for function {func.__name__} "
                        f"failed: {str(e)}. Retrying in {wait_time:.2f} seconds..."
                    )
                    
                    time.sleep(wait_time)
                    wait_time *= self.backoff_factor
        
        return wrapper
