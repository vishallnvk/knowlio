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

# Auto-registration configuration
AUTO_REGISTRATION_ENABLED = True
DEFAULT_AUTO_REGISTRATION_ROLE = "PUBLISHER"
DEFAULT_AUTO_REGISTRATION_GROUP = "Publisher"
AUTO_REGISTRATION_AUTH_PROVIDER = "Google"

# Cognito group management
COGNITO_GROUP_ROLE_MAPPING = {
    "Admin": "ADMIN",
    "Publisher": "PUBLISHER", 
    "Consumer": "CONSUMER"
}

# Logging configuration for auth flow
AUTH_FLOW_LOGGING_ENABLED = True
