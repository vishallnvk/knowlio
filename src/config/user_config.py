"""
Configuration for user-related settings
"""

# DynamoDB table names
USERS_TABLE_NAME = "users"

# Retry configuration
DEFAULT_RETRY_MAX_ATTEMPTS = 3
DEFAULT_RETRY_INITIAL_WAIT = 1.0

# Validation patterns
EMAIL_REGEX_PATTERN = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

# Field configurations
IMMUTABLE_FIELDS = ["user_id", "created_at"]
INDEXED_FIELDS = ["role", "email"]
REQUIRED_FIELDS = ["email", "role"]

# Valid roles (referenced from RoleBasedAuth.VALID_ROLES)
VALID_ROLES = ["ADMIN", "PUBLISHER", "CONSUMER"]

# Pagination defaults
DEFAULT_PAGINATION_LIMIT = 50
