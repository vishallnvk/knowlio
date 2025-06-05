# Amazon OpenSearch Serverless Integration

This document describes the integration of Amazon OpenSearch Serverless with the Knowlio application. This serverless search service provides powerful full-text search capabilities without the operational overhead of managing search infrastructure.

## Features

- **Serverless Architecture**: No cluster to manage, scales automatically with your workload
- **Pay-per-use Pricing**: Pay only for what you use, no upfront costs
- **Search-optimized Collections**: Specifically designed for full-text search workloads
- **Simplified Security**: Built-in encryption and access control
- **Auto-scaling**: Automatically scales compute and storage based on demand
- **Comprehensive Search**: Full-featured search capabilities with OpenSearch DSL support

## Architecture

The OpenSearch Serverless integration consists of:

1. **Collection**: A serverless OpenSearch collection specifically configured for search workloads
2. **Security Policies**: 
   - Encryption Policy: Uses AWS-owned keys for data encryption
   - Network Policy: Controls network access to the collection
   - Access Policy: Defines who can access indexes and data
3. **IAM Permissions**: Lambda functions use IAM permissions to access OpenSearch Serverless
4. **Helper Module**: A Python module to interact with OpenSearch Serverless API

## Deployment Components

### OpenSearch Serverless Construct

Located at `infrastructure/app_constructs/opensearch_serverless_construct.py`, this CDK construct:

- Creates a serverless collection for full-text search
- Sets up encryption, network, and data access policies
- Configures dependencies between resources to ensure proper creation order
- Outputs the collection endpoint and dashboard URL

### KnowlioStack Integration

The `KnowlioStack` in `infrastructure/stacks/knowlio_stack.py` has been updated to:

- Create an OpenSearch Serverless collection with appropriate settings
- Set up IAM permissions for Lambda to access the collection using `aoss:*` actions
- Pass environment variables to Lambda for OpenSearch Serverless access
- Store references to the collection for cross-stack usage

## Helper Module

The OpenSearch helper at `src/helpers/aws_service_helpers/opensearch_helper.py` supports both standard OpenSearch Service and OpenSearch Serverless:

### Key Features
- Automatic detection of OpenSearch Serverless endpoints
- Support for both OpenSearch Service (`es`) and OpenSearch Serverless (`aoss`) authentication
- Default index management from environment variables
- Complete CRUD operations for documents
- Advanced search functionality
- Bulk operations for efficient data handling
- Retry logic with exponential backoff

## Environment Variables

When using OpenSearch Serverless, the following environment variables are set:

- `OPENSEARCH_ENDPOINT`: The collection endpoint (e.g., `[collection-id].us-east-1.aoss.amazonaws.com`)
- `OPENSEARCH_COLLECTION_NAME`: The name of the collection
- `OPENSEARCH_INDEX_NAME`: The name of the index for storing content (default: `content-index`)
- `OPENSEARCH_REGION`: The AWS region where the collection is deployed
- `OPENSEARCH_SERVERLESS`: Set to `"true"` to indicate OpenSearch Serverless usage

## Usage Examples

### Basic Setup

```python
from src.helpers.aws_service_helpers.opensearch_helper import OpenSearchHelper

# Initialize the helper (all parameters from environment variables)
helper = OpenSearchHelper()

# Create a content index with mappings
mapping = {
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "title": {"type": "text", "analyzer": "standard"},
            "content": {"type": "text", "analyzer": "standard"},
            "author": {"type": "keyword"},
            "tags": {"type": "keyword"},
            "createdAt": {"type": "date"}
        }
    }
}
helper.create_index("content-index", mapping)
```

### Document Operations

```python
# Add a document
doc_id = "book-123"
document = {
    "id": doc_id,
    "title": "Introduction to OpenSearch",
    "content": "OpenSearch is a distributed search and analytics engine...",
    "author": "user-456",
    "tags": ["search", "tutorial"],
    "createdAt": "2025-06-05T10:15:30Z"
}
helper.index_document("content-index", doc_id, document)

# Get a document
retrieved = helper.get_document("content-index", doc_id)
print(retrieved["_source"]["title"])

# Update a document
updates = {"title": "Updated: Introduction to OpenSearch"}
helper.update_document("content-index", doc_id, updates)

# Delete a document
helper.delete_document("content-index", doc_id)
```

### Search Examples

```python
# Simple keyword search
query = {
    "query": {
        "match": {
            "content": "OpenSearch"
        }
    }
}
results = helper.search("content-index", query)

# Advanced search with filters
advanced_query = {
    "query": {
        "bool": {
            "must": [
                {"match": {"content": "serverless"}},
                {"term": {"author": "user-456"}}
            ],
            "filter": [
                {"term": {"tags": "tutorial"}}
            ]
        }
    },
    "sort": [
        {"createdAt": {"order": "desc"}}
    ]
}
results = helper.search("content-index", advanced_query, from_=0, size=25)
```

### Bulk Operations

```python
# Bulk index multiple documents
documents = [
    {
        "id": "doc-1",
        "title": "First Document",
        "content": "Content for document 1"
    },
    {
        "id": "doc-2",
        "title": "Second Document",
        "content": "Content for document 2"
    }
]
helper.bulk_index("content-index", documents, id_field="id")

# Bulk delete multiple documents
doc_ids = ["doc-1", "doc-2"]
helper.bulk_delete("content-index", doc_ids)
```

## Security Considerations

OpenSearch Serverless has built-in security features:

1. **Encryption at Rest**: All data is encrypted using AWS-owned keys
2. **Network Security**: Network access is controlled through security policies
3. **Data Access Control**: Fine-grained access control through data access policies
4. **IAM Authentication**: All requests are authenticated and authorized using IAM credentials

## Cost Considerations

OpenSearch Serverless uses a pay-per-use pricing model:

- Compute: Charged per OCU-hour (OpenSearch Compute Unit)
- Storage: Charged per GB-month for indexed data
- Data Transfer: Standard AWS data transfer rates apply

This model is typically more cost-effective for variable or unpredictable workloads compared to the provisioned OpenSearch Service.

## Dashboard Access

You can access the OpenSearch Dashboard at the following URL (after deployment):
`https://[collection-endpoint]/_dashboards/`

This provides a web interface for:
- Visualizing data
- Creating saved searches
- Monitoring the collection
- Testing queries interactively

## Migration from OpenSearch Service

If you're migrating from OpenSearch Service to OpenSearch Serverless:

1. The OpenSearchHelper class automatically detects whether you're using OpenSearch Service or OpenSearch Serverless
2. API operations remain the same, but the authentication mechanism differs
3. IAM permissions use the `aoss:*` actions instead of `es:*` actions
4. Security is managed through policies instead of resource-based policies
