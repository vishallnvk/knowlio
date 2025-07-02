"""
Processor for S3 upload operations, including multipart uploads.
"""

from typing import Dict, List, Any, Optional
import json

from helpers.common_helper.common_helper import require_keys
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.common_helper.auth_helper import require_role, get_authenticated_user_id
from helpers.common_helper.auth_context import AuthContext
from helpers.aws_service_helpers.s3_helper import S3Helper
from sync_processor_registry.processor_registry import ProcessorRegistry
from sync_processors.base_processor import BaseProcessor
from config.s3_config import (
    CONTENT_BUCKET_NAME,
    DEFAULT_CONTENT_TYPE,
    DEFAULT_PRESIGNED_URL_EXPIRY
)

logger = LoggerHelper(__name__).get_logger()


@ProcessorRegistry.register("s3_upload")
class S3UploadProcessor(BaseProcessor):
    def __init__(self):
        # Initialize with required bucket from config
        self.s3_helper = S3Helper(CONTENT_BUCKET_NAME)
        
        super().__init__({
            # Regular upload methods
            "generate_presigned_upload_url": self._generate_presigned_upload_url,
            "generate_presigned_download_url": self._generate_presigned_download_url,
            
            # Multipart upload methods
            "initiate_multipart_upload": self._initiate_multipart_upload,
            "generate_presigned_part_upload_url": self._generate_presigned_part_upload_url,
            "complete_multipart_upload": self._complete_multipart_upload,
            "abort_multipart_upload": self._abort_multipart_upload,
            "list_parts": self._list_parts,
        })

    # Regular upload methods
    @require_role(["ADMIN", "PUBLISHER"])
    def _generate_presigned_upload_url(self, payload: Dict) -> Dict[str, Any]:
        """
        Generate a presigned URL for direct file upload to S3.
        Requires ADMIN or PUBLISHER role.
        
        Args:
            payload: Dict with key, content_type (optional), expires_in (optional)
            
        Returns:
            Dict with presigned URL
        """
        try:
            require_keys(payload, ["key"])
            key = payload["key"]
            content_type = payload.get("content_type", DEFAULT_CONTENT_TYPE)
            expires_in = int(payload.get("expires_in", DEFAULT_PRESIGNED_URL_EXPIRY))
            
            # Add user tracking metadata to the key
            auth_context = AuthContext.from_payload(payload)
            if auth_context.is_authenticated():
                # Add user ID as metadata in the key name or metadata
                if '/' not in key:
                    # Add user ID as prefix for organization
                    key = f"{auth_context.user_id}/{key}"
                
                logger.info(f"User {auth_context.user_id} ({auth_context.role}) generating presigned URL for upload: {key}")
            
            url = self.s3_helper.generate_presigned_upload_url(
                key=key,
                content_type=content_type,
                expires_in=expires_in
            )
            
            return {"url": url, "key": key}
        except Exception as e:
            logger.error(f"Error generating presigned upload URL: {str(e)}")
            return {"error": f"Failed to generate presigned upload URL: {str(e)}"}

    def _generate_presigned_download_url(self, payload: Dict) -> Dict[str, Any]:
        """
        Generate a presigned URL for file download from S3.
        
        Args:
            payload: Dict with key, expires_in (optional)
            
        Returns:
            Dict with presigned URL
        """
        try:
            require_keys(payload, ["key"])
            key = payload["key"]
            expires_in = int(payload.get("expires_in", DEFAULT_PRESIGNED_URL_EXPIRY))
            
            # Log download requests
            auth_context = AuthContext.from_payload(payload)
            if auth_context.is_authenticated():
                logger.info(f"User {auth_context.user_id} ({auth_context.role}) generating download URL for: {key}")
            
            url = self.s3_helper.generate_presigned_download_url(
                key=key,
                expires_in=expires_in
            )
            
            return {"url": url, "key": key}
        except Exception as e:
            logger.error(f"Error generating presigned download URL: {str(e)}")
            return {"error": f"Failed to generate presigned download URL: {str(e)}"}

    # Multipart upload methods
    @require_role(["ADMIN", "PUBLISHER"])
    def _initiate_multipart_upload(self, payload: Dict) -> Dict[str, Any]:
        """
        Initiate a multipart upload process.
        Requires ADMIN or PUBLISHER role.
        
        Args:
            payload: Dict with key, content_type (optional)
            
        Returns:
            Dict with upload_id and other details
        """
        try:
            require_keys(payload, ["key"])
            key = payload["key"]
            content_type = payload.get("content_type", DEFAULT_CONTENT_TYPE)
            
            # Add user tracking information
            auth_context = AuthContext.from_payload(payload)
            if auth_context.is_authenticated():
                # Add user ID as prefix for organization
                if '/' not in key:
                    key = f"{auth_context.user_id}/{key}"
                    
                logger.info(f"User {auth_context.user_id} ({auth_context.role}) initiating multipart upload for: {key}")
                
                # Add metadata that will be saved with the file
                metadata = payload.get("metadata", {})
                metadata["uploaded_by"] = auth_context.user_id
                metadata["role"] = auth_context.role
                payload["metadata"] = metadata
            
            result = self.s3_helper.initiate_multipart_upload(
                key=key,
                content_type=content_type,
                metadata=payload.get("metadata")
            )
            
            return result
        except Exception as e:
            logger.error(f"Error initiating multipart upload: {str(e)}")
            return {"error": f"Failed to initiate multipart upload: {str(e)}"}

    @require_role(["ADMIN", "PUBLISHER"])
    def _generate_presigned_part_upload_url(self, payload: Dict) -> Dict[str, Any]:
        """
        Generate a presigned URL for uploading a specific part of a multipart upload.
        Requires ADMIN or PUBLISHER role.
        
        Args:
            payload: Dict with key, upload_id, part_number, expires_in (optional)
            
        Returns:
            Dict with presigned URL and part details
        """
        try:
            require_keys(payload, ["key", "upload_id", "part_number"])
            key = payload["key"]
            upload_id = payload["upload_id"]
            part_number = int(payload["part_number"])
            expires_in = int(payload.get("expires_in", DEFAULT_PRESIGNED_URL_EXPIRY))
            
            # Log the request
            user_id = get_authenticated_user_id(payload)
            if user_id:
                logger.info(f"User {user_id} generating presigned URL for part {part_number} of upload {upload_id}")
            
            result = self.s3_helper.generate_presigned_part_upload_url(
                key=key,
                upload_id=upload_id,
                part_number=part_number,
                expires_in=expires_in
            )
            
            return result
        except Exception as e:
            logger.error(f"Error generating presigned part upload URL: {str(e)}")
            return {"error": f"Failed to generate presigned part upload URL: {str(e)}"}

    @require_role(["ADMIN", "PUBLISHER"])
    def _complete_multipart_upload(self, payload: Dict) -> Dict[str, Any]:
        """
        Complete a multipart upload after all parts have been uploaded.
        Requires ADMIN or PUBLISHER role.
        
        Args:
            payload: Dict with key, upload_id, parts (list of dicts with PartNumber and ETag)
            
        Returns:
            Dict with details of the completed upload
        """
        try:
            require_keys(payload, ["key", "upload_id", "parts"])
            key = payload["key"]
            upload_id = payload["upload_id"]
            parts = payload["parts"]
            
            # Validate parts format
            if not isinstance(parts, list) or not all(isinstance(p, dict) and 'PartNumber' in p and 'ETag' in p for p in parts):
                return {"error": "Parts must be a list of dicts with PartNumber and ETag"}
            
            # Log completion
            auth_context = AuthContext.from_payload(payload)
            if auth_context.is_authenticated():
                logger.info(f"User {auth_context.user_id} ({auth_context.role}) completing multipart upload for: {key}")
            
            result = self.s3_helper.complete_multipart_upload(
                key=key,
                upload_id=upload_id,
                parts=parts
            )
            
            return result
        except Exception as e:
            logger.error(f"Error completing multipart upload: {str(e)}")
            return {"error": f"Failed to complete multipart upload: {str(e)}"}

    @require_role(["ADMIN", "PUBLISHER"])
    def _abort_multipart_upload(self, payload: Dict) -> Dict[str, Any]:
        """
        Abort a multipart upload and remove any uploaded parts.
        Requires ADMIN or PUBLISHER role.
        
        Args:
            payload: Dict with key, upload_id
            
        Returns:
            Dict with status of the abort operation
        """
        try:
            require_keys(payload, ["key", "upload_id"])
            key = payload["key"]
            upload_id = payload["upload_id"]
            
            # Log abort operation
            user_id = get_authenticated_user_id(payload)
            if user_id:
                logger.info(f"User {user_id} aborting multipart upload {upload_id} for key {key}")
            
            result = self.s3_helper.abort_multipart_upload(
                key=key,
                upload_id=upload_id
            )
            
            return result
        except Exception as e:
            logger.error(f"Error aborting multipart upload: {str(e)}")
            return {"error": f"Failed to abort multipart upload: {str(e)}"}

    @require_role(["ADMIN", "PUBLISHER"])
    def _list_parts(self, payload: Dict) -> Dict[str, Any]:
        """
        List all parts that have been uploaded for a specific multipart upload.
        Requires ADMIN or PUBLISHER role.
        
        Args:
            payload: Dict with key, upload_id
            
        Returns:
            Dict with details of all uploaded parts
        """
        try:
            require_keys(payload, ["key", "upload_id"])
            key = payload["key"]
            upload_id = payload["upload_id"]
            
            # Log the action
            user_id = get_authenticated_user_id(payload)
            if user_id:
                logger.info(f"User {user_id} listing parts for upload {upload_id}")
            
            result = self.s3_helper.list_parts(
                key=key,
                upload_id=upload_id
            )
            
            return result
        except Exception as e:
            logger.error(f"Error listing parts for upload: {str(e)}")
            return {"error": f"Failed to list parts for upload: {str(e)}"}
