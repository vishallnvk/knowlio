
from typing import Any, Dict


class ProcessorEventInput:
    def __init__(self, data: Dict[str, Any]):
        self.processor_name = data.get("processor_name")
        self.payload = data.get("payload", {})

        self._validate()

    def _validate(self):
        if not isinstance(self.processor_name, str) or not self.processor_name.strip():
            raise ValueError("processor_name must be a non-empty string")
        if not isinstance(self.payload, dict):
            raise ValueError("payload must be a dictionary")
