"""
API Gateway route configuration for Knowlio REST API.
Defines all processor actions as REST API endpoints with their HTTP methods and paths.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ApiRoute:
    """Configuration for a single API route"""
    method: str
    path: str
    processor_name: str
    action: str
    description: str
    path_parameters: Optional[List[str]] = None
    query_parameters: Optional[List[str]] = None


class KnowlioApiRoutes:
    """Central configuration for all Knowlio API routes"""
    
    @staticmethod
    def get_all_routes() -> List[ApiRoute]:
        """Return all API routes for the Knowlio system"""
        return [
            # User Management Routes
            ApiRoute(
                method="POST",
                path="users/register",
                processor_name="user",
                action="register_user",
                description="Register a new user",
            ),
            ApiRoute(
                method="GET",
                path="users/{user_id}",
                processor_name="user",
                action="get_user_profile",
                description="Get user profile by ID",
                path_parameters=["user_id"]
            ),
            ApiRoute(
                method="PUT",
                path="users/{user_id}",
                processor_name="user",
                action="update_user_profile",
                description="Update user profile",
                path_parameters=["user_id"]
            ),
            ApiRoute(
                method="GET",
                path="users",
                processor_name="user",
                action="list_users_by_role",
                description="List users by role with pagination",
                query_parameters=["role", "limit", "pagination_token"]
            ),
            ApiRoute(
                method="POST",
                path="users/search",
                processor_name="user",
                action="search_users",
                description="Search users with flexible criteria",
            ),
            ApiRoute(
                method="PATCH",
                path="users/{user_id}/admin",
                processor_name="user",
                action="admin_update_user",
                description="Admin-only generic field update",
                path_parameters=["user_id"]
            ),
            
            # Content Management Routes
            ApiRoute(
                method="POST",
                path="content/metadata",
                processor_name="content",
                action="upload_content_metadata",
                description="Upload content metadata",
            ),
            ApiRoute(
                method="GET",
                path="content/{content_id}",
                processor_name="content",
                action="get_content_details",
                description="Get content details by ID",
                path_parameters=["content_id"]
            ),
            ApiRoute(
                method="PUT",
                path="content/{content_id}",
                processor_name="content",
                action="update_content_metadata",
                description="Update content metadata",
                path_parameters=["content_id"]
            ),
            ApiRoute(
                method="PATCH",
                path="content/{content_id}/attribute/{attribute}",
                processor_name="content",
                action="update_content_attribute",
                description="Update a single content attribute",
                path_parameters=["content_id", "attribute"]
            ),
            ApiRoute(
                method="GET",
                path="content",
                processor_name="content",
                action="list_content_by_publisher",
                description="List content by publisher with pagination",
                query_parameters=["publisher_id", "limit", "pagination_token"]
            ),
            ApiRoute(
                method="POST",
                path="content/search",
                processor_name="content",
                action="search_content",
                description="Search content with flexible parameters and pagination",
            ),
            ApiRoute(
                method="POST",
                path="content/{content_id}/archive",
                processor_name="content",
                action="archive_content",
                description="Archive content",
                path_parameters=["content_id"]
            ),
            ApiRoute(
                method="GET",
                path="content/query/{attribute}/{value}",
                processor_name="content",
                action="query_by_attribute",
                description="Query content by any attribute",
                path_parameters=["attribute", "value"],
                query_parameters=["limit", "pagination_token"]
            ),
            
            # License Management Routes
            ApiRoute(
                method="POST",
                path="licenses",
                processor_name="license",
                action="create_license",
                description="Create a new license",
            ),
            ApiRoute(
                method="GET",
                path="licenses/{license_id}",
                processor_name="license",
                action="get_license",
                description="Get license by ID",
                path_parameters=["license_id"]
            ),
            ApiRoute(
                method="GET",
                path="licenses",
                processor_name="license",
                action="list_licenses_by_consumer",
                description="List licenses by consumer",
                query_parameters=["consumer_id"]
            ),
            ApiRoute(
                method="GET",
                path="licenses/content/{content_id}",
                processor_name="license",
                action="list_licenses_by_content",
                description="List licenses by content",
                path_parameters=["content_id"]
            ),
            ApiRoute(
                method="POST",
                path="licenses/{license_id}/revoke",
                processor_name="license",
                action="revoke_license",
                description="Revoke a license",
                path_parameters=["license_id"]
            ),
            
            # Analytics Routes
            ApiRoute(
                method="POST",
                path="analytics/access",
                processor_name="analytics",
                action="log_content_access",
                description="Log content access",
            ),
            ApiRoute(
                method="GET",
                path="analytics/content/{content_id}",
                processor_name="analytics",
                action="get_usage_report_by_content",
                description="Get usage report by content",
                path_parameters=["content_id"]
            ),
            ApiRoute(
                method="GET",
                path="analytics/consumer/{consumer_id}",
                processor_name="analytics",
                action="get_usage_report_by_consumer",
                description="Get usage report by consumer",
                path_parameters=["consumer_id"]
            ),
            
            # Google Books API Routes
            ApiRoute(
                method="GET",
                path="books/{isbn}",
                processor_name="google_books",
                action="get_book_details",
                description="Get complete book details by ISBN",
                path_parameters=["isbn"]
            ),
            ApiRoute(
                method="GET",
                path="books/{isbn}/filtered",
                processor_name="google_books",
                action="get_book_details_filtered",
                description="Get filtered book details by ISBN",
                path_parameters=["isbn"],
                query_parameters=["fields"]
            ),
            ApiRoute(
                method="GET",
                path="books/author/{author_name}",
                processor_name="google_books",
                action="get_books_by_author",
                description="Get all books by a specific author",
                path_parameters=["author_name"],
                query_parameters=["max_results"]
            ),
            ApiRoute(
                method="GET",
                path="books/author/{author_name}/filtered",
                processor_name="google_books",
                action="get_books_by_author_filtered",
                description="Get filtered book details for all books by a specific author",
                path_parameters=["author_name"],
                query_parameters=["fields", "max_results"]
            ),
            
            # S3 Upload Routes
            ApiRoute(
                method="POST",
                path="uploads/url",
                processor_name="s3_upload",
                action="generate_presigned_upload_url",
                description="Generate a presigned URL for direct file upload to S3"
            ),
            ApiRoute(
                method="GET",
                path="uploads/download/{key}",
                processor_name="s3_upload",
                action="generate_presigned_download_url",
                description="Generate a presigned URL for file download from S3",
                path_parameters=["key"]
            ),
            
            # S3 Multipart Upload Routes
            ApiRoute(
                method="POST",
                path="uploads/multipart/init",
                processor_name="s3_upload",
                action="initiate_multipart_upload",
                description="Initiate a multipart upload process"
            ),
            ApiRoute(
                method="POST",
                path="uploads/multipart/part-url",
                processor_name="s3_upload",
                action="generate_presigned_part_upload_url",
                description="Generate a presigned URL for uploading a specific part"
            ),
            ApiRoute(
                method="POST",
                path="uploads/multipart/complete",
                processor_name="s3_upload",
                action="complete_multipart_upload",
                description="Complete a multipart upload after all parts have been uploaded"
            ),
            ApiRoute(
                method="DELETE",
                path="uploads/multipart/abort",
                processor_name="s3_upload",
                action="abort_multipart_upload",
                description="Abort a multipart upload and remove any uploaded parts"
            ),
            ApiRoute(
                method="GET",
                path="uploads/multipart/parts",
                processor_name="s3_upload",
                action="list_parts",
                description="List all parts that have been uploaded for a specific multipart upload"
            ),
        ]
    
    @staticmethod
    def get_routes_by_processor(processor_name: str) -> List[ApiRoute]:
        """Get all routes for a specific processor"""
        return [route for route in KnowlioApiRoutes.get_all_routes() 
                if route.processor_name == processor_name]
    
    @staticmethod
    def get_route_by_method_and_path(method: str, path: str) -> Optional[ApiRoute]:
        """Get a specific route by HTTP method and path"""
        for route in KnowlioApiRoutes.get_all_routes():
            if route.method == method and route.path == path:
                return route
        return None
