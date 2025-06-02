#!/usr/bin/env python3
"""
REST API Examples for Knowlio API Gateway
Demonstrates all available REST endpoints with example requests and responses
"""

import json
import requests
from typing import Dict, Any

# Base URL will be output from CDK deployment
# Replace with your actual API Gateway URL after deployment
BASE_URL = "https://your-api-id.execute-api.us-west-2.amazonaws.com/prod"

class KnowlioApiClient:
    """Client for interacting with Knowlio REST API"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict[str, Any]:
        """Make HTTP request to the API"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            raise

    # User Management APIs
    def register_user(self, user_data: Dict) -> Dict[str, Any]:
        """POST /users/register"""
        return self._make_request('POST', '/users/register', data=user_data)
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """GET /users/{user_id}"""
        return self._make_request('GET', f'/users/{user_id}')
    
    def update_user_profile(self, user_id: str, updates: Dict) -> Dict[str, Any]:
        """PUT /users/{user_id}"""
        return self._make_request('PUT', f'/users/{user_id}', data=updates)
    
    def list_users_by_role(self, role: str) -> Dict[str, Any]:
        """GET /users?role={role}"""
        return self._make_request('GET', '/users', params={'role': role})

    # Content Management APIs
    def upload_content_metadata(self, content_data: Dict) -> Dict[str, Any]:
        """POST /content/metadata"""
        return self._make_request('POST', '/content/metadata', data=content_data)
    
    def get_content_details(self, content_id: str) -> Dict[str, Any]:
        """GET /content/{content_id}"""
        return self._make_request('GET', f'/content/{content_id}')
    
    def update_content_metadata(self, content_id: str, updates: Dict) -> Dict[str, Any]:
        """PUT /content/{content_id}"""
        return self._make_request('PUT', f'/content/{content_id}', data=updates)
    
    def list_content_by_publisher(self, publisher_id: str) -> Dict[str, Any]:
        """GET /content?publisher_id={publisher_id}"""
        return self._make_request('GET', '/content', params={'publisher_id': publisher_id})
    
    def archive_content(self, content_id: str) -> Dict[str, Any]:
        """POST /content/{content_id}/archive"""
        return self._make_request('POST', f'/content/{content_id}/archive')

    # License Management APIs
    def create_license(self, license_data: Dict) -> Dict[str, Any]:
        """POST /licenses"""
        return self._make_request('POST', '/licenses', data=license_data)
    
    def get_license(self, license_id: str) -> Dict[str, Any]:
        """GET /licenses/{license_id}"""
        return self._make_request('GET', f'/licenses/{license_id}')
    
    def list_licenses_by_consumer(self, consumer_id: str) -> Dict[str, Any]:
        """GET /licenses?consumer_id={consumer_id}"""
        return self._make_request('GET', '/licenses', params={'consumer_id': consumer_id})
    
    def list_licenses_by_content(self, content_id: str) -> Dict[str, Any]:
        """GET /licenses/content/{content_id}"""
        return self._make_request('GET', f'/licenses/content/{content_id}')
    
    def revoke_license(self, license_id: str) -> Dict[str, Any]:
        """POST /licenses/{license_id}/revoke"""
        return self._make_request('POST', f'/licenses/{license_id}/revoke')

    # Analytics APIs
    def log_content_access(self, access_data: Dict) -> Dict[str, Any]:
        """POST /analytics/access"""
        return self._make_request('POST', '/analytics/access', data=access_data)
    
    def get_usage_report_by_content(self, content_id: str) -> Dict[str, Any]:
        """GET /analytics/content/{content_id}"""
        return self._make_request('GET', f'/analytics/content/{content_id}')
    
    def get_usage_report_by_consumer(self, consumer_id: str) -> Dict[str, Any]:
        """GET /analytics/consumer/{consumer_id}"""
        return self._make_request('GET', f'/analytics/consumer/{consumer_id}')


def print_example_requests():
    """Print example curl commands for all endpoints"""
    
    examples = [
        {
            "title": "User Management",
            "requests": [
                {
                    "description": "Register a new user",
                    "curl": """curl -X POST "$BASE_URL/users/register" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "role": "PUBLISHER",
    "organization": "Example Corp"
  }'"""
                },
                {
                    "description": "Get user profile",
                    "curl": """curl -X GET "$BASE_URL/users/user-123" \\
  -H "Content-Type: application/json" """
                },
                {
                    "description": "Update user profile",
                    "curl": """curl -X PUT "$BASE_URL/users/user-123" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "John Smith",
    "organization": "New Corp"
  }'"""
                },
                {
                    "description": "List users by role",
                    "curl": """curl -X GET "$BASE_URL/users?role=PUBLISHER" \\
  -H "Content-Type: application/json" """
                }
            ]
        },
        {
            "title": "Content Management",
            "requests": [
                {
                    "description": "Upload content metadata",
                    "curl": """curl -X POST "$BASE_URL/content/metadata" \\
  -H "Content-Type: application/json" \\
  -d '{
    "publisher_id": "pub-123",
    "title": "My Dataset",
    "type": "DATASET",
    "description": "A comprehensive dataset for ML training"
  }'"""
                },
                {
                    "description": "Get content details",
                    "curl": """curl -X GET "$BASE_URL/content/content-123" \\
  -H "Content-Type: application/json" """
                },
                {
                    "description": "Update content metadata",
                    "curl": """curl -X PUT "$BASE_URL/content/content-123" \\
  -H "Content-Type: application/json" \\
  -d '{
    "title": "Updated Dataset Title",
    "description": "Updated description"
  }'"""
                },
                {
                    "description": "List content by publisher",
                    "curl": """curl -X GET "$BASE_URL/content?publisher_id=pub-123" \\
  -H "Content-Type: application/json" """
                },
                {
                    "description": "Archive content",
                    "curl": """curl -X POST "$BASE_URL/content/content-123/archive" \\
  -H "Content-Type: application/json" """
                }
            ]
        },
        {
            "title": "License Management", 
            "requests": [
                {
                    "description": "Create a license",
                    "curl": """curl -X POST "$BASE_URL/licenses" \\
  -H "Content-Type: application/json" \\
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
    },
    "version": "v2.3"
  }'"""
                },
                {
                    "description": "Get license details",
                    "curl": """curl -X GET "$BASE_URL/licenses/license-123" \\
  -H "Content-Type: application/json" """
                },
                {
                    "description": "List licenses by consumer",
                    "curl": """curl -X GET "$BASE_URL/licenses?consumer_id=consumer-456" \\
  -H "Content-Type: application/json" """
                },
                {
                    "description": "List licenses by content",
                    "curl": """curl -X GET "$BASE_URL/licenses/content/content-123" \\
  -H "Content-Type: application/json" """
                },
                {
                    "description": "Revoke a license",
                    "curl": """curl -X POST "$BASE_URL/licenses/license-123/revoke" \\
  -H "Content-Type: application/json" """
                }
            ]
        },
        {
            "title": "Analytics",
            "requests": [
                {
                    "description": "Log content access",
                    "curl": """curl -X POST "$BASE_URL/analytics/access" \\
  -H "Content-Type: application/json" \\
  -d '{
    "content_id": "content-123",
    "consumer_id": "consumer-456",
    "ip_address": "192.0.2.10",
    "user_agent": "Mozilla/5.0",
    "access_type": "VIEW",
    "publisher_id": "pub-123",
    "region": "NA",
    "metadata": {
      "session_id": "sess-111"
    }
  }'"""
                },
                {
                    "description": "Get usage report by content",
                    "curl": """curl -X GET "$BASE_URL/analytics/content/content-123" \\
  -H "Content-Type: application/json" """
                },
                {
                    "description": "Get usage report by consumer",
                    "curl": """curl -X GET "$BASE_URL/analytics/consumer/consumer-456" \\
  -H "Content-Type: application/json" """
                }
            ]
        }
    ]
    
    print("=" * 80)
    print("KNOWLIO REST API EXAMPLES")
    print("=" * 80)
    print("\nReplace $BASE_URL with your actual API Gateway URL from CDK output")
    print("Example: export BASE_URL=https://abcd1234.execute-api.us-west-2.amazonaws.com/prod")
    
    for category in examples:
        print(f"\n{'=' * 60}")
        print(f"{category['title'].upper()}")
        print('=' * 60)
        
        for i, request in enumerate(category['requests'], 1):
            print(f"\n{i}. {request['description']}")
            print("-" * 40)
            print(request['curl'])
            print()


def run_integration_tests():
    """Run integration tests against the API (update BASE_URL first)"""
    
    print("Integration Tests")
    print("=" * 50)
    print(f"Testing against: {BASE_URL}")
    print("Make sure to update BASE_URL with your actual API Gateway URL")
    
    client = KnowlioApiClient(BASE_URL)
    
    try:
        # Test user registration
        print("\n1. Testing user registration...")
        user_data = {
            "name": "Test User",
            "email": "test@example.com",
            "role": "PUBLISHER"
        }
        result = client.register_user(user_data)
        print(f"✓ User registered: {result}")
        user_id = result.get('user_id')
        
        if user_id:
            # Test get user profile
            print(f"\n2. Testing get user profile...")
            profile = client.get_user_profile(user_id)
            print(f"✓ User profile: {profile}")
        
        print("\n✓ Integration tests completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Integration test failed: {e}")
        print("Make sure your API is deployed and BASE_URL is correct")


if __name__ == "__main__":
    print_example_requests()
    
    # Uncomment to run integration tests (update BASE_URL first)
    # run_integration_tests()
