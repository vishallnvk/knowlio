"""
OpenSearch Helper Module

This module provides helper functions for interacting with Amazon OpenSearch Service
and Amazon OpenSearch Serverless.
"""

import os
import json
import time
import boto3
import requests
from requests_aws4auth import AWS4Auth
from botocore.exceptions import ClientError
from typing import Dict, List, Any, Optional, Union


class OpenSearchHelper:
    """Helper class for Amazon OpenSearch operations."""

    def __init__(self, endpoint: str = None, region: str = None, is_serverless: bool = None):
        """
        Initialize the OpenSearch helper.
        
        Args:
            endpoint: OpenSearch endpoint (without https://). 
                     If not provided, it will be read from environment variables.
            region: AWS region. If not provided, it will be read from environment variables.
            is_serverless: Whether this is OpenSearch Serverless. 
                          If not provided, will detect from environment variables or endpoint.
        """
        self.endpoint = endpoint or os.environ.get('OPENSEARCH_ENDPOINT')
        if not self.endpoint:
            raise ValueError("OpenSearch endpoint not provided and OPENSEARCH_ENDPOINT environment variable not set")
        
        # Ensure endpoint doesn't have protocol prefix
        if self.endpoint.startswith('https://'):
            self.endpoint = self.endpoint[8:]
        
        self.region = region or os.environ.get('AWS_REGION') or 'us-west-2'
        self.collection_name = os.environ.get('OPENSEARCH_COLLECTION_NAME')
        self.index_name = os.environ.get('OPENSEARCH_INDEX_NAME') or 'content-index'
        
        # Determine if we're using OpenSearch Serverless
        if is_serverless is not None:
            self.is_serverless = is_serverless
        else:
            self.is_serverless = os.environ.get('OPENSEARCH_SERVERLESS', '').lower() == 'true' or 'aoss' in self.endpoint
        
        # Set the service name based on whether we're using OpenSearch Serverless
        self.service = 'aoss' if self.is_serverless else 'es'
        self.url = f'https://{self.endpoint}'
        self.auth = self._get_aws_auth()
        self.headers = {'Content-Type': 'application/json'}
        
        # Configure retry parameters
        self.max_retries = 3
        self.initial_backoff = 1  # seconds
    
    def _get_aws_auth(self) -> AWS4Auth:
        """
        Get AWS authentication credentials.
        
        Returns:
            AWS4Auth object for request signing
        """
        credentials = boto3.Session().get_credentials()
        return AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            self.region,
            self.service,
            session_token=credentials.token
        )
    
    def _make_request(self, method: str, path: str, body: dict = None, params: dict = None) -> dict:
        """
        Make a request to the OpenSearch domain with exponential backoff retry logic.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path starting with '/'. Should not include domain name.
            body: Request body as a dictionary, will be converted to JSON
            params: URL parameters
            
        Returns:
            Response as a dictionary
            
        Raises:
            Exception: If the request fails after all retries
        """
        url = f'{self.url}{path}'
        json_body = json.dumps(body) if body else None
        
        retry_count = 0
        backoff_time = self.initial_backoff
        
        while retry_count < self.max_retries:
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    auth=self.auth,
                    headers=self.headers,
                    data=json_body,
                    params=params
                )
                
                # Raise exception for HTTP errors
                response.raise_for_status()
                
                # Parse JSON response
                if response.text and len(response.text) > 0:
                    return response.json()
                return {}
                
            except requests.exceptions.RequestException as e:
                retry_count += 1
                
                # If this was our last retry, raise the exception
                if retry_count >= self.max_retries:
                    raise Exception(f"Failed to make request to OpenSearch: {str(e)}")
                
                # Otherwise, sleep with exponential backoff
                time.sleep(backoff_time)
                backoff_time *= 2  # Exponential backoff
    
    # Index Management
    
    def create_index(self, index_name: str = None, mapping: dict = None) -> dict:
        """
        Create a new index with optional mapping.
        
        Args:
            index_name: Name of the index to create. If not provided, uses the default index.
            mapping: Index mapping configuration
            
        Returns:
            OpenSearch API response
        """
        index_name = index_name or self.index_name
        return self._make_request('PUT', f'/{index_name}', body=mapping)
    
    def delete_index(self, index_name: str = None) -> dict:
        """
        Delete an index.
        
        Args:
            index_name: Name of the index to delete. If not provided, uses the default index.
            
        Returns:
            OpenSearch API response
        """
        index_name = index_name or self.index_name
        return self._make_request('DELETE', f'/{index_name}')
    
    def get_index_settings(self, index_name: str = None) -> dict:
        """
        Get settings for an index.
        
        Args:
            index_name: Name of the index. If not provided, uses the default index.
            
        Returns:
            Index settings as a dictionary
        """
        index_name = index_name or self.index_name
        return self._make_request('GET', f'/{index_name}/_settings')
    
    def get_index_mapping(self, index_name: str = None) -> dict:
        """
        Get field mappings for an index.
        
        Args:
            index_name: Name of the index. If not provided, uses the default index.
            
        Returns:
            Index mapping as a dictionary
        """
        index_name = index_name or self.index_name
        return self._make_request('GET', f'/{index_name}/_mapping')
    
    # Document Operations
    
    def index_document(self, index_name: str, doc_id: str, document: dict) -> dict:
        """
        Index a document with the given ID.
        
        Args:
            index_name: Name of the index
            doc_id: Document ID
            document: Document data as a dictionary
            
        Returns:
            OpenSearch API response
        """
        return self._make_request('PUT', f'/{index_name}/_doc/{doc_id}', body=document)
    
    def get_document(self, index_name: str, doc_id: str) -> dict:
        """
        Get a document by ID.
        
        Args:
            index_name: Name of the index
            doc_id: Document ID
            
        Returns:
            Document data as a dictionary
        """
        return self._make_request('GET', f'/{index_name}/_doc/{doc_id}')
    
    def update_document(self, index_name: str, doc_id: str, document: dict) -> dict:
        """
        Update a document by ID.
        
        Args:
            index_name: Name of the index
            doc_id: Document ID
            document: Document fields to update as a dictionary
            
        Returns:
            OpenSearch API response
        """
        body = {'doc': document}
        return self._make_request('POST', f'/{index_name}/_update/{doc_id}', body=body)
    
    def delete_document(self, index_name: str, doc_id: str) -> dict:
        """
        Delete a document by ID.
        
        Args:
            index_name: Name of the index
            doc_id: Document ID
            
        Returns:
            OpenSearch API response
        """
        return self._make_request('DELETE', f'/{index_name}/_doc/{doc_id}')
    
    # Search Operations
    
    def search(self, index_name: str, query: dict, from_: int = 0, size: int = 10) -> dict:
        """
        Search for documents.
        
        Args:
            index_name: Name of the index
            query: Query as a dictionary (OpenSearch Query DSL)
            from_: Starting document offset for pagination
            size: Number of documents to return
            
        Returns:
            Search results as a dictionary
        """
        params = {
            'from': from_,
            'size': size
        }
        return self._make_request('POST', f'/{index_name}/_search', body=query, params=params)
    
    # Bulk Operations
    
    def bulk_index(self, index_name: str, documents: List[dict], id_field: str = 'id') -> dict:
        """
        Index multiple documents in one bulk request.
        
        Args:
            index_name: Name of the index
            documents: List of document dictionaries
            id_field: Field to use as document ID
            
        Returns:
            OpenSearch API response
        """
        bulk_operations = []
        
        for doc in documents:
            # Get the document ID from the specified field
            doc_id = doc.get(id_field)
            if not doc_id:
                raise ValueError(f"Document is missing required '{id_field}' field for ID")
                
            # Add the index action
            action = {"index": {"_index": index_name, "_id": doc_id}}
            bulk_operations.append(action)
            # Add the document data
            bulk_operations.append(doc)
        
        # Convert to newline-delimited JSON
        bulk_body = "\n".join([json.dumps(op) for op in bulk_operations]) + "\n"
        
        # Make the request directly to avoid double JSON encoding
        url = f'{self.url}/_bulk'
        response = requests.post(
            url, 
            headers={"Content-Type": "application/x-ndjson"},
            auth=self.auth,
            data=bulk_body
        )
        
        # Raise exception for HTTP errors
        response.raise_for_status()
        
        # Parse JSON response
        return response.json()
    
    def bulk_delete(self, index_name: str, doc_ids: List[str]) -> dict:
        """
        Delete multiple documents in one bulk request.
        
        Args:
            index_name: Name of the index
            doc_ids: List of document IDs to delete
            
        Returns:
            OpenSearch API response
        """
        bulk_operations = []
        
        for doc_id in doc_ids:
            # Add the delete action
            action = {"delete": {"_index": index_name, "_id": doc_id}}
            bulk_operations.append(action)
        
        # Convert to newline-delimited JSON
        bulk_body = "\n".join([json.dumps(op) for op in bulk_operations]) + "\n"
        
        # Make the request directly to avoid double JSON encoding
        url = f'{self.url}/_bulk'
        response = requests.post(
            url, 
            headers={"Content-Type": "application/x-ndjson"},
            auth=self.auth,
            data=bulk_body
        )
        
        # Raise exception for HTTP errors
        response.raise_for_status()
        
        # Parse JSON response
        return response.json()
