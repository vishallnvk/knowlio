# Knowlio REST API Documentation

## Overview

This document describes the complete REST API implementation for the Knowlio content licensing and analytics platform. The API is built using AWS CDK with API Gateway and Lambda Proxy Integration.

## Architecture

```
Client Request → API Gateway → Lambda (api_gateway_handler) → Processor → DynamoDB/S3
```

### Key Components

1. **API Gateway**: Single REST API with Lambda Proxy Integration
2. **Lambda Handler**: `api_gateway_handler.py` - Transforms REST requests to processor events
3. **Route Configuration**: `infrastructure/config/api_routes.py` - Centralized route definitions
4. **API Gateway Construct**: `infrastructure/app_constructs/api_gateway_construct.py` - CDK construct for API setup
5. **Processors**: User, Content, License, and Analytics processors

## API Endpoints

### User Management

| Method | Endpoint | Description | Processor Action |
|--------|----------|-------------|------------------|
| POST | `/users/register` | Register a new user | `user.register_user` |
| GET | `/users/{user_id}` | Get user profile | `user.get_user_profile` |
| PUT | `/users/{user_id}` | Update user profile | `user.update_user_profile` |
| GET | `/users?role={role}` | List users by role | `user.list_users_by_role` |

### Content Management

| Method | Endpoint | Description | Processor Action |
|--------|----------|-------------|------------------|
| POST | `/content/metadata` | Upload content metadata | `content.upload_content_metadata` |
| GET | `/content/{content_id}` | Get content details | `content.get_content_details` |
| PUT | `/content/{content_id}` | Update content metadata | `content.update_content_metadata` |
| GET | `/content?publisher_id={id}` | List content by publisher | `content.list_content_by_publisher` |
| POST | `/content/{content_id}/archive` | Archive content | `content.archive_content` |

### License Management

| Method | Endpoint | Description | Processor Action |
|--------|----------|-------------|------------------|
| POST | `/licenses` | Create a license | `license.create_license` |
| GET | `/licenses/{license_id}` | Get license details | `license.get_license` |
| GET | `/licenses?consumer_id={id}` | List licenses by consumer | `license.list_licenses_by_consumer` |
| GET | `/licenses/content/{content_id}` | List licenses by content | `license.list_licenses_by_content` |
| POST | `/licenses/{license_id}/revoke` | Revoke a license | `license.revoke_license` |

### Analytics

| Method | Endpoint | Description | Processor Action |
|--------|----------|-------------|------------------|
| POST | `/analytics/access` | Log content access | `analytics.log_content_access` |
| GET | `/analytics/content/{content_id}` | Get usage report by content | `analytics.get_usage_report_by_content` |
| GET | `/analytics/consumer/{consumer_id}` | Get usage report by consumer | `analytics.get_usage_report_by_consumer` |

## Request/Response Format

### Standard Response Format
```json
{
  "statusCode": 200,
  "headers": {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
  },
  "body": {
    // Response data here
  }
}
```

### Error Response Format
```json
{
  "statusCode": 400|404|500,
  "headers": { /* CORS headers */ },
  "body": {
    "error": "Error Type",
    "message": "Detailed error message"
  }
}
```

## Example Requests

### 1. Register a User
```bash
curl -X POST "https://your-api-url/prod/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "role": "PUBLISHER",
    "organization": "Example Corp"
  }'
```

### 2. Create a License
```bash
curl -X POST "https://your-api-url/prod/licenses" \
  -H "Content-Type: application/json" \
  -d '{
    "content_id": "content-123",
    "publisher_id": "pub-123", 
    "consumer_id": "consumer-456",
    "license_terms": {
      "start_date": "2024-06-01",
      "end_date": "2025-06-01",
      "region": "Global",
      "tier": "Enterprise",
      "access_scope": "Read-Only"
    }
  }'
```

### 3. Log Content Access
```bash
curl -X POST "https://your-api-url/prod/analytics/access" \
  -H "Content-Type: application/json" \
  -d '{
    "content_id": "content-123",
    "consumer_id": "consumer-456",
    "ip_address": "192.0.2.10",
    "user_agent": "Mozilla/5.0",
    "access_type": "VIEW",
    "publisher_id": "pub-123",
    "region": "NA"
  }'
```

## Configuration Files

### Route Configuration (`infrastructure/config/api_routes.py`)

Routes are defined using a clean, maintainable data structure:

```python
@dataclass
class ApiRoute:
    method: str
    path: str
    processor_name: str
    action: str
    description: str
    path_parameters: Optional[List[str]] = None
    query_parameters: Optional[List[str]] = None
```

### API Gateway Construct (`infrastructure/app_constructs/api_gateway_construct.py`)

Features:
- Automatic route creation from configuration
- CORS enabled for all routes
- Lambda Proxy Integration
- Resource caching for efficient route building
- Throttling and stage configuration

## Deployment

### Prerequisites
- AWS CDK v2 installed
- AWS CLI configured
- Python 3.11+

### Deploy Infrastructure
```bash
# Deploy DynamoDB tables
cdk deploy DynamoDBStack

# Deploy Lambda and API Gateway
cdk deploy KnowlioStack
```

### Get API URL
After deployment, the API Gateway URL will be output:
```
KnowlioStack.ApiUrl = https://abcd1234.execute-api.us-west-2.amazonaws.com/prod/
```

## Testing

### Using the Python Client
```python
from rest_api_examples import KnowlioApiClient

client = KnowlioApiClient("https://your-api-url/prod")

# Register a user
result = client.register_user({
    "name": "Test User",
    "email": "test@example.com",
    "role": "PUBLISHER"
})
```

### Using curl
See `rest_api_examples.py` for comprehensive curl examples for all endpoints.

## Security Features

- **CORS**: Enabled for all routes with proper headers
- **IAM**: Lambda has minimal required permissions for DynamoDB, S3, and CloudWatch
- **Input Validation**: All requests validated at processor level
- **Error Handling**: Comprehensive error handling with proper HTTP status codes

## Monitoring

- **CloudWatch Logs**: All requests logged with detailed information
- **API Gateway Metrics**: Built-in metrics for request count, latency, errors
- **Lambda Metrics**: Execution duration, memory usage, error rates
- **Throttling**: Rate limiting configured (1000 requests/second, 2000 burst)

## Database Schema

### DynamoDB Tables
- `users` - User profiles and authentication
- `content` - Content metadata and status
- `licenses` - License agreements and terms
- `usage_logs` - Analytics and access logging

### S3 Integration
- Analytics exports stored in `knowlio-exports` bucket
- Logs exported in JSONL format for Athena compatibility

## Backwards Compatibility

The API handler supports both:
1. **REST API requests** (from API Gateway)
2. **Direct processor events** (for backwards compatibility)

This ensures existing direct Lambda invocations continue to work while adding REST API capabilities.

## Best Practices Implemented

1. **Separation of Concerns**: Configuration, routing, and business logic are separate
2. **Clean Architecture**: Processors remain unchanged, new handler layer added
3. **Comprehensive Logging**: Detailed logs for debugging and monitoring
4. **Error Handling**: Proper HTTP status codes and error messages
5. **CORS Support**: Full CORS support for web applications
6. **Documentation**: Comprehensive examples and documentation
7. **Testing**: Integration test framework provided

## File Structure

```
infrastructure/
├── config/
│   └── api_routes.py          # Route configuration
├── app_constructs/
│   └── api_gateway_construct.py # API Gateway CDK construct
└── stacks/
    └── knowlio_stack.py       # Main CDK stack

src/
└── handlers/
    └── api_gateway_handler.py # API Gateway Lambda handler

rest_api_examples.py           # Testing and examples
REST_API_README.md            # This documentation
```

## Next Steps

1. **Authentication**: Add API keys or JWT authentication
2. **Rate Limiting**: Implement per-user rate limiting
3. **API Versioning**: Add versioning support (v1, v2, etc.)
4. **OpenAPI Spec**: Generate OpenAPI/Swagger documentation
5. **SDK Generation**: Generate client SDKs for different languages
6. **Caching**: Add API Gateway caching for read operations
