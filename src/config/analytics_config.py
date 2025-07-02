"""
Configuration for analytics-related settings
"""

# DynamoDB table names
USAGE_LOGS_TABLE_NAME = "usage_logs"

# S3 bucket names
EXPORT_BUCKET_NAME = "knowlio-exports"

# Default values
DEFAULT_ACCESS_TYPE = "VIEW"
DEFAULT_REGION = "UNKNOWN"
DEFAULT_PUBLISHER_ID = "UNKNOWN"
DEFAULT_EXPORT_FORMAT = "jsonl"

# Report settings
RECENT_LOGS_LIMIT = 10

# Pagination defaults
DEFAULT_PAGINATION_LIMIT = 50
