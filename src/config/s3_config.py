"""
Configuration for S3-related settings
"""

# S3 bucket names
CONTENT_BUCKET_NAME = "knowlio-content-bucket"

# Default values
DEFAULT_CONTENT_TYPE = "application/octet-stream"
DEFAULT_PRESIGNED_URL_EXPIRY = 3600  # 1 hour in seconds

# Upload settings
MAX_UPLOAD_SIZE = 5 * 1024 * 1024 * 1024  # 5GB
MIN_MULTIPART_SIZE = 5 * 1024 * 1024  # 5MB minimum for multipart
