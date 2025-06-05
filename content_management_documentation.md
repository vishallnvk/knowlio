# Content Management System Documentation

This document describes the enhanced implementation of the content management system in Knowlio, detailing the architecture, key components, and usage patterns.

## Architecture Overview

The content management system follows a modular, layered architecture:

1. **API Layer**: REST endpoints defined in `api_routes.py`
2. **Processor Layer**: `ContentProcessor` that handles business logic and validations
3. **Helper Layer**: `ContentHelper` that encapsulates database operations with retry logic
4. **Data Layer**: DynamoDB-backed persistence using `DynamoDBHelper`

## Key Components

### Content Model

The `ContentModel` class defines the flexible content structure with the following attributes:

- `content_id`: Unique identifier (UUID)
- `publisher_id`: ID of the content publisher
- `title`: Content title
- `type`: Content type (BOOK, VIDEO, AUDIO, DATASET, TEXT)
- `tags`: List of content tags
- `description`: Content description
- `metadata`: Flexible JSON field for type-specific attributes
- `status`: Content lifecycle status (DRAFT, ACTIVE, ARCHIVED)
- `file_key`: S3 key for the content blob
- Workflow status fields:
  - `rag_status`: RAG processing status (ENABLED, DISABLED)
  - `training_status`: Model training status (ENABLED, DISABLED)
  - `licensing_status`: Licensing status (ENABLED, DISABLED)
- Timestamps (`created_at`, `updated_at`)

### Content Helper

The `ContentHelper` class handles database operations with:

- Generic attribute management
- Comprehensive data validation
- Type-specific metadata handling
- Efficient search and query capabilities
- Pagination support
- Robust error handling and retry logic

### Generic Attribute Management

The system implements a flexible attribute management approach:

- **Top-level attributes**: Generic methods for updating any content property
- **Nested metadata**: Support for dot notation to modify nested fields
- **Type validation**: Automatic validation based on content type
- **Status consistency**: Enforced status transitions and validation

### API Endpoints

The content management API offers these endpoints:

- `POST /content/metadata`: Create new content metadata
- `GET /content/{content_id}`: Get content details
- `PUT /content/{content_id}`: Update content metadata
- `PATCH /content/{content_id}/attribute/{attribute}`: Update single attribute
- `GET /content`: List content by publisher with pagination
- `POST /content/search`: Search content with flexible criteria
- `POST /content/{content_id}/archive`: Archive content
- `GET /content/query/{attribute}/{value}`: Query content by attribute

## Content Type Support

### Book Content

Books can include type-specific metadata:
- `pages`: Number of pages
- `format`: File format (PDF, EPUB, etc.)
- `isbn`: ISBN identifier
- `author`: Book author(s)
- `publication_year`: Publication year
- Other book-specific fields

### Video Content

Videos can include:
- `duration_minutes`: Video length
- `resolution`: Video quality
- `format`: File format
- `presenter`: Video presenter/creator
- Other video-specific fields

### Dataset Content

Datasets can include:
- `record_count`: Number of records
- `file_type`: Data format (CSV, JSON, etc.)
- `domain`: Dataset domain/category
- `languages`: List of languages
- Other dataset-specific fields

## Search & Query Capabilities

The system provides powerful search capabilities:

- **Type-Based Filtering**: Query content by type
- **Publisher Filtering**: List content by publisher
- **Status Filtering**: Filter by lifecycle or workflow status
- **Tag-Based Filtering**: Search by content tags
- **Text Search**: Search in title, description
- **Metadata Search**: Query by type-specific attributes
- **Combined Criteria**: Mix and match any search parameters
- **Efficient Index Usage**: Automatically uses GSIs when applicable

## Pagination Implementation

The system implements an efficient pagination mechanism:

1. **Token-Based**: Uses DynamoDB's `LastEvaluatedKey` encoded as a Base64 token
2. **Stateless**: No server-side state is maintained between pagination calls
3. **Consistent API**: All list/search operations support pagination with the same pattern

Example pagination usage:
```json
// First page request
{
  "publisher_id": "publisher-123",
  "limit": 10
}

// Response with pagination token
{
  "contents": [...],
  "count": 10,
  "pagination": {
    "next_token": "eyJjb250ZW50X2lkIjoiYWJjMTIzIn0=",
    "has_more": true
  }
}

// Next page request
{
  "publisher_id": "publisher-123",
  "limit": 10,
  "pagination_token": "eyJjb250ZW50X2lkIjoiYWJjMTIzIn0="
}
```

## Infrastructure & Database

The system leverages DynamoDB with Global Secondary Indexes (GSIs) for efficient operations:

- **Primary Key**: `content_id` (partition key)
- **GSIs**:
  - `publisher_id-index`: For querying content by publisher
  - `type-index`: For type-based queries
  - `status-index`: For status-based queries

## Sample Usage

### Creating Book Content

```json
{
  "processor_name": "content",
  "action": "upload_content_metadata",
  "payload": {
    "publisher_id": "publisher-123",
    "title": "Advanced Machine Learning",
    "type": "BOOK",
    "tags": ["AI", "Machine Learning", "Python"],
    "description": "A comprehensive guide to machine learning techniques",
    "metadata": {
      "pages": 450,
      "format": "PDF",
      "isbn": "978-1-234567-89-0",
      "author": "Dr. Jane Smith",
      "publication_year": 2024
    }
  }
}
```

### Updating a Specific Attribute

```json
{
  "processor_name": "content",
  "action": "update_content_attribute",
  "payload": {
    "content_id": "c71e3c00-1b2f-4a5d-abcd-ef1234567890",
    "attribute": "metadata.pages",
    "value": 475
  }
}
```

### Enabling RAG Processing

```json
{
  "processor_name": "content",
  "action": "update_content_attribute",
  "payload": {
    "content_id": "c71e3c00-1b2f-4a5d-abcd-ef1234567890",
    "attribute": "rag_status",
    "value": "ENABLED"
  }
}
```

### Searching Content by Various Criteria

```json
{
  "processor_name": "content",
  "action": "search_content",
  "payload": {
    "type": "BOOK",
    "tags": ["AI"],
    "metadata.author": "Smith",
    "rag_status": "ENABLED",
    "limit": 10
  }
}
```

## Best Practices

The content management implementation follows these best practices:

- **Flexible Schema Design**: Support for diverse content types
- **Generic Attribute Management**: Easily adapt to new content types and fields
- **Separation of Concerns**: Clear boundaries between layers
- **Defensive Coding**: Thorough validation and error handling
- **Consistent API Patterns**: Standardized request/response formats
- **Comprehensive Logging**: Detailed logs for debugging and monitoring
- **Robust Error Handling**: Graceful error responses
- **Efficient Database Access**: Index-aware queries for performance

## Extension Points

The system is designed to be easily extended:

1. Add new content types by updating `ContentModel.VALID_TYPES`
2. Add type-specific validation in `ContentHelper.update_content_metadata`
3. Extend search capabilities by enhancing `_matches_search_criteria`
4. Add new workflow fields to track additional processing states
5. Create new API endpoints by extending the route definitions and processor methods
