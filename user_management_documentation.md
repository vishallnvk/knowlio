# User Management System Documentation

This document describes the implementation of the user management system in Knowlio, detailing the architecture, key components, and usage patterns.

## Architecture Overview

The user management system follows a modular, layered architecture:

1. **API Layer**: REST endpoints defined in `api_routes.py`
2. **Processor Layer**: `UserProcessor` that handles business logic and validations
3. **Helper Layer**: `UserHelper` that encapsulates database operations with retry logic
4. **Authorization Layer**: Decoupled `RoleBasedAuth` system for access control
5. **Data Layer**: DynamoDB-backed persistence using `DynamoDBHelper`

## Key Components

### User Model

The `UserModel` class defines the core user structure with the following attributes:

- `user_id`: Unique identifier (UUID)
- `email`: User's email address (unique)
- `role`: User's role (PUBLISHER, CONSUMER, or ADMIN)
- `name`: User's display name
- `organization`: User's company or organization
- `auth_provider`: Authentication provider (COGNITO, GOOGLE)
- `created_at`: Timestamp of user creation
- `metadata`: Flexible JSON field for role-specific attributes

### User Helper

The `UserHelper` class handles database operations with:

- Enhanced data validation
- Email uniqueness checks
- Role validation
- Role-specific metadata validation
- Retry logic for resilience
- Pagination support for listing operations
- Flexible search capabilities

### Authorization System

The decoupled `RoleBasedAuth` class provides:

- Role-based access control
- Role hierarchy (ADMIN > PUBLISHER, ADMIN > CONSUMER)
- Permission checking
- A reusable decorator for securing methods

### API Endpoints

The user management API offers these endpoints:

- `POST /users/register`: Register a new user
- `GET /users/{user_id}`: Get user profile
- `PUT /users/{user_id}`: Update user profile
- `GET /users`: List users by role with pagination
- `POST /users/search`: Search users with flexible criteria
- `PATCH /users/{user_id}/admin`: Admin-only field updates

## Role-Specific Features

### Publisher Features

Publishers can:

- Register with publisher-specific metadata:
  - `legal_entity`: Legal entity name
  - `content_types`: List of supported content types
  - `website`: Publisher's website
  - `region`: Geographical region

### Consumer Features

Consumers can:

- Register with consumer-specific metadata:
  - `license_tier`: Enterprise, Pro, Basic, etc.
  - `api_quota`: API usage limits
  - `use_case`: Purpose of content access
  - `integration_level`: Level of integration

### Admin Features

Admins have:

- Access to all user records
- Ability to update any user field
- Role inheritance for accessing PUBLISHER and CONSUMER features

## Pagination Implementation

The system implements an efficient pagination mechanism:

1. **Token-Based**: Uses DynamoDB's `LastEvaluatedKey` encoded as a Base64 token
2. **Stateless**: No server-side state is maintained between pagination calls
3. **Consistent API**: All list/search operations support pagination with the same pattern

Example pagination usage:
```json
// First page request
{
  "role": "PUBLISHER",
  "limit": 10
}

// Response with pagination token
{
  "users": [...],
  "count": 10,
  "pagination": {
    "next_token": "eyJjb250ZW50X2lkIjoiYWJjMTIzIn0=",
    "has_more": true
  }
}

// Next page request
{
  "role": "PUBLISHER",
  "limit": 10,
  "pagination_token": "eyJjb250ZW50X2lkIjoiYWJjMTIzIn0="
}
```

## Advanced Search Capabilities

The system supports flexible searching across user records:

- **Direct Field Matching**: Search by email, name, role, etc.
- **Partial String Matching**: Case-insensitive substring matches
- **Nested Field Searching**: Access metadata fields using dot notation
- **Efficient Index Usage**: Automatically uses GSIs when available
- **Fallback Scanning**: Falls back to scan operation when indexes aren't available

Example search usage:
```json
// Search by email domain
{
  "email": "example.com"
}

// Search by metadata field
{
  "role": "CONSUMER", 
  "metadata.license_tier": "enterprise"
}

// Search with pagination
{
  "organization": "Corp",
  "limit": 20
}
```

## Retry Mechanism

All AWS service calls in the user management system are protected by a retry mechanism:

- Automatic retry on transient failures
- Configurable retry count (default: 3)
- Exponential backoff
- Comprehensive error logging
- Support for specific exception types

## Best Practices

The user management implementation follows these best practices:

- **Separation of Concerns**: Clear boundaries between layers
- **Defensive Coding**: Thorough validation and error handling
- **API Consistency**: Standardized request/response patterns
- **Decoupled Authentication**: Authorization separate from business logic
- **Comprehensive Logging**: Detailed logs for debugging and monitoring
- **Graceful Error Handling**: User-friendly error responses
- **Scalable Design**: Pagination for handling large datasets

## Sample Usage

### Registering a Publisher

```json
{
  "processor_name": "user",
  "action": "register_user",
  "payload": {
    "email": "pub@example.com",
    "role": "PUBLISHER",
    "name": "Pearson",
    "organization": "Pearson Inc.",
    "auth_provider": "GOOGLE",
    "metadata": {
      "legal_entity": "Pearson Publishing Inc.",
      "content_types": ["books", "videos"],
      "website": "https://pearson.com",
      "region": "NA"
    }
  }
}
```

### Searching Users by Criteria

```json
{
  "processor_name": "user",
  "action": "search_users",
  "payload": {
    "organization": "Corp",
    "metadata.region": "NA",
    "limit": 10
  }
}
```

### Admin User Update

```json
{
  "processor_name": "user",
  "action": "admin_update_user",
  "payload": {
    "user_id": "370c9000-011f-47b5-b905-00d94d42868d",
    "field": "role",
    "value": "ADMIN"
  }
}
```

## Extension Points

The system is designed to be easily extended:

1. Add new user roles by updating `RoleBasedAuth.VALID_ROLES` and `RoleBasedAuth.ROLE_HIERARCHY`
2. Add role-specific metadata validation in `_validate_role_specific_metadata`
3. Add new search capabilities by updating the `_matches_search_criteria` method
4. Add new API endpoints by extending the `UserProcessor` registration map
