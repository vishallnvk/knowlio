"""
Configuration for license-related settings
"""

# DynamoDB table names
LICENSES_TABLE_NAME = "licenses"

# Retry configuration
DEFAULT_RETRY_MAX_ATTEMPTS = 3
DEFAULT_RETRY_INITIAL_WAIT = 1.0

# Indexed fields for efficient querying
INDEXED_FIELDS = ["consumer_id", "content_id", "publisher_id", "status"]

# Valid license statuses
VALID_LICENSE_STATUSES = ["ACTIVE", "REVOKED"]

# Pagination defaults
DEFAULT_PAGINATION_LIMIT = 50
