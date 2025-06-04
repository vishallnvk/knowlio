# Content Search Documentation

This document provides details on using the content search functionality in the Knowlio system, which allows flexible searching across different content types with special handling for books.

## Overview

The content search functionality enables:
- Searching content by common fields like publisher, title, and tags
- Type-specific searching for specialized content types
- Book-specific search capabilities as the first supported specialized type
- Completely flexible parameter passing for future extensibility

## Search Parameters

The search functionality accepts any combination of the following parameters:

### Common Parameters (all content types)
- `publisher_id`: Filter by content publisher
- `type`: Content type, including "book", "text", "video", "audio"
- `title`: Full or partial title to search for (case-insensitive)
- `tags`: List of tags to filter by (matches if content has any of the specified tags)
- `status`: Content status ("DRAFT", "ACTIVE", "ARCHIVED")

### Pagination Parameters
- `limit`: Maximum number of items to return in a single request
- `pagination_token`: Token for retrieving the next page of results

### Book-Specific Parameters
When `type` is "book", any additional parameters will be checked against the content's metadata fields. For example:

- `author`: Search for books by a specific author
- `isbn`: Search for a book with a specific ISBN
- `year`: Publication year
- `publisher_name`: Name of the publisher (as opposed to publisher_id which is the internal ID)
- Any other metadata field specific to books

## Usage Examples

### 1. Basic Search by Publisher

```json
{
  "processor_name": "content",
  "action": "search_content",
  "payload": {
    "publisher_id": "pub123"
  }
}
```

### 2. Search for Active Books with Title Containing "Python"

```json
{
  "processor_name": "content",
  "action": "search_content",
  "payload": {
    "type": "book",
    "title": "python",
    "status": "ACTIVE"
  }
}
```

### 3. Search for Books by Author and Tags

```json
{
  "processor_name": "content",
  "action": "search_content", 
  "payload": {
    "type": "book",
    "tags": ["programming", "education"],
    "author": "Martin"
  }
}
```

### 4. Mixed Parameter Search for Books

```json
{
  "processor_name": "content",
  "action": "search_content",
  "payload": {
    "type": "book",
    "publisher_id": "pub123",
    "title": "design patterns",
    "author": "Gamma",
    "year": "1994"
  }
}
```

## API Reference

### Search Content API

**Endpoint:** POST /content/search  
**Action:** search_content  
**Description:** Search content with flexible parameters and pagination

**Request Body:**
```json
{
  "publisher_id": "...",  // optional
  "type": "book",         // optional
  "title": "...",         // optional
  "tags": ["...", "..."], // optional
  "status": "ACTIVE",     // optional
  "field1": "value1",     // custom fields (checked in metadata)
  "field2": "value2",     // custom fields (checked in metadata)
  "limit": 20,            // optional: maximum items per page
  "pagination_token": "..." // optional: token for next page
}
```

**Response:**
```json
{
  "contents": [
    {
      "content_id": "...",
      "publisher_id": "...",
      "title": "...",
      "type": "...",
      "tags": ["...", "..."],
      "description": "...",
      "metadata": {
        "field1": "value1",
        "field2": "value2"
      },
      "status": "...",
      "file_key": "...",
      "created_at": "..."
    },
    // Additional results...
  ],
  "count": 5,
  "total_scanned": 10,
  "pagination": {
    "next_token": "eyJjb250ZW50X2lkIjoiYWJjMTIzIn0=",
    "has_more": true
  }
}
```

## Implementation Details

The search functionality is built on top of DynamoDB and follows this process:

1. If `publisher_id` is provided, perform a query operation using the publisher_id index
2. Otherwise, perform a scan operation to search all content
3. Apply filters for all provided parameters:
   - Common fields are matched directly
   - Book-specific fields are matched against metadata
   - String fields use case-insensitive partial matching
   - Tags use "any match" semantics (content matches if it has any of the specified tags)

## Future Extensions

The search functionality is designed to be extended with additional content type-specific handling. The current implementation supports books, with placeholders for:

- Text content
- Video content
- Audio content

Each content type can have specialized search parameters appropriate for that media type.

## Pagination

The search and list functionality supports pagination to handle large result sets efficiently. The pagination system works as follows:

### How Pagination Works

1. When making a request, specify a `limit` parameter to control how many results to return per page
2. The response will include a `pagination` object if there are more results available
3. The `pagination` object contains:
   - `next_token`: A base64-encoded token that represents the last evaluated key
   - `has_more`: Boolean indicating if there are more results available
4. To fetch the next page, include the `pagination_token` parameter in your next request with the value from `next_token`

### Example Pagination Flow

1. Initial request with limit:
```json
{
  "publisher_id": "pub123",
  "limit": 10
}
```

2. Check response for pagination:
```json
{
  "contents": [...],
  "count": 10,
  "pagination": {
    "next_token": "eyJjb250ZW50X2lkIjoiYWJjMTIzIn0=",
    "has_more": true
  }
}
```

3. Fetch next page using the token:
```json
{
  "publisher_id": "pub123",
  "limit": 10,
  "pagination_token": "eyJjb250ZW50X2lkIjoiYWJjMTIzIn0="
}
```

### Pagination Implementation Details

- Pagination tokens are base64-encoded JSON containing the last evaluated key from DynamoDB
- Each token is specific to the query that generated it and should not be modified
- Tokens have no expiration but may become invalid if the underlying data changes significantly

## Performance Considerations

For best performance, consider:

1. Always include `publisher_id` when possible to use the more efficient query operation
2. Limit the scope of your search with specific parameters
3. Use appropriate `limit` values based on your UI requirements (typically 10-20 items per page)
4. Store pagination tokens for backward navigation if needed
