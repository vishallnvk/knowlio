"""
Configuration for content-related settings
"""

# DynamoDB table names
CONTENT_TABLE_NAME = "content"

# Default status values
DEFAULT_WORKFLOW_STATUS = "DISABLED"

# Content types
CONTENT_TYPES = {
    "BOOK": "BOOK",
    "AUDIO": "AUDIO"
}

# Valid status values (for reference, actual enums are in content_status.py)
VALID_CONTENT_STATUSES = ["DRAFT", "ACTIVE", "ARCHIVED"]
VALID_WORKFLOW_STATUSES = ["ENABLED", "DISABLED"]

# Workflow status field names
WORKFLOW_STATUS_FIELDS = ["rag_status", "training_status", "licensing_status"]

# Retry configuration
DEFAULT_RETRY_MAX_ATTEMPTS = 3
DEFAULT_RETRY_INITIAL_WAIT = 1.0

# Pagination defaults
DEFAULT_PAGINATION_LIMIT = 50
