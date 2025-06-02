# Knowlio Architecture Overview

## Clean Architecture Implementation

The Knowlio project now follows clean architecture principles with clear separation of concerns between infrastructure, configuration, and business logic.

## Directory Structure

```
infrastructure/
├── app_constructs/           # Generic, reusable CDK constructs
│   ├── api_gateway_construct.py    # Generic API Gateway wrapper
│   ├── dynamodb_construct.py       # Generic DynamoDB wrapper
│   ├── iam_role_construct.py       # Generic IAM role wrapper
│   └── lambda_construct.py         # Generic Lambda wrapper
│
├── config/                   # Business logic and configuration
│   ├── api_routes.py               # Knowlio-specific route definitions
│   └── knowlio_api_config.py       # Knowlio API configuration builder
│
└── stacks/                   # CDK stacks that compose constructs
    ├── knowlio_dynamodb_tables_stack.py
    └── knowlio_stack.py

src/
├── handlers/                 # Lambda handlers
│   ├── api_gateway_handler.py      # REST API handler
│   └── synchronous_lambda_handler.py # Direct processor handler
│
├── models/                   # Data models
├── processors/               # Business logic processors  
└── helpers/                  # Utility functions
```

## Architecture Layers

### 1. Infrastructure Layer (Pure CDK Constructs)
**Location**: `infrastructure/app_constructs/`

These are generic, reusable CDK constructs that act as pure infrastructure wrappers:

- **`ApiGatewayConstruct`**: Generic API Gateway with Lambda integration
- **`DynamoDBConstruct`**: Generic DynamoDB table creation
- **`IamRoleConstruct`**: Generic IAM role creation  
- **`LambdaConstruct`**: Generic Lambda function creation

**Key Characteristics**:
- ✅ No business logic
- ✅ Reusable across projects
- ✅ Configuration through props/parameters
- ✅ Follows CDK best practices

### 2. Configuration Layer (Business Logic)
**Location**: `infrastructure/config/`

Contains Knowlio-specific business logic and configuration:

- **`api_routes.py`**: Defines all Knowlio API endpoints with their processor mappings
- **`knowlio_api_config.py`**: Builds configuration for the generic API Gateway construct

**Key Characteristics**:
- ✅ Business logic separated from infrastructure
- ✅ Easy to modify API endpoints
- ✅ Clear mapping between REST endpoints and processors
- ✅ Maintainable configuration

### 3. Stack Layer (Composition)
**Location**: `infrastructure/stacks/`

CDK stacks that compose the generic constructs with business-specific configuration:

```python
# Clean composition in KnowlioStack
api_props = KnowlioApiConfig.get_api_gateway_props()
api_routes = KnowlioApiConfig.get_route_definitions()

api_gateway = ApiGatewayConstruct(
    self, "KnowlioApiGateway",
    lambda_function=lambda_fn.function,
    props=api_props,
    routes=api_routes
)
```

## Benefits of This Architecture

### 1. **Separation of Concerns**
- Infrastructure code is separate from business logic
- Generic constructs can be reused in other projects
- Configuration changes don't require touching infrastructure code

### 2. **Maintainability**
- Adding new API endpoints only requires updating `api_routes.py`
- API Gateway settings can be modified in `knowlio_api_config.py`
- Infrastructure constructs are stable and rarely need changes

### 3. **Reusability**
- API Gateway construct can be used for any REST API project
- DynamoDB construct works for any table configuration
- Clean interfaces make constructs portable

### 4. **Testability**
- Business logic can be unit tested independently
- Infrastructure can be tested separately
- Clear contracts between layers

### 5. **Readability**
- Each file has a single responsibility
- Configuration is declarative and easy to understand
- Stack composition is clean and explicit

## Example: Adding a New API Endpoint

To add a new endpoint, you only need to modify the configuration layer:

```python
# In api_routes.py, add to KnowlioApiRoutes.get_all_routes():
ApiRoute(
    method="GET",
    path="reports/{report_id}",
    processor_name="reports",
    action="get_report",
    description="Get report by ID",
    path_parameters=["report_id"]
)
```

That's it! The generic infrastructure automatically:
- Creates the API Gateway route
- Sets up CORS headers
- Configures Lambda integration
- Handles path parameters

## Comparison with Previous Architecture

### Before (Coupled)
```python
# Business logic mixed with infrastructure
class ApiGatewayConstruct(Construct):
    def __init__(self, ...):
        # Hardcoded Knowlio-specific routes
        self._create_users_routes()
        self._create_content_routes()
        # etc...
```

### After (Decoupled)
```python
# Generic infrastructure
class ApiGatewayConstruct(Construct):
    def __init__(self, ..., props, routes):
        self.add_routes(routes)  # Generic route creation

# Separate business configuration
class KnowlioApiConfig:
    @staticmethod
    def get_route_definitions():
        return [/* Knowlio-specific routes */]
```

## Best Practices Implemented

1. **Single Responsibility Principle**: Each class/file has one job
2. **Open/Closed Principle**: Constructs are open for extension, closed for modification
3. **Dependency Inversion**: High-level modules don't depend on low-level modules
4. **Configuration over Code**: Business rules are data, not hardcoded logic
5. **Composition over Inheritance**: Stacks compose constructs rather than extending them

## Future Extensibility

This architecture makes it easy to:

- **Add new APIs**: Just modify configuration files
- **Support multiple environments**: Different configurations per environment
- **Create new projects**: Reuse the generic constructs
- **Add authentication**: Extend the API Gateway construct
- **Support API versioning**: Add version parameters to configuration

The clean separation ensures that infrastructure changes don't break business logic and vice versa.
