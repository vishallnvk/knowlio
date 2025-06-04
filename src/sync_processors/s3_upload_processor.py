"""
Processor for S3 upload operations, including multipart uploads.
"""

from typing import Dict, List, Any, Optional
import json

from helpers.common_helper.common_helper import require_keys
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.aws_service_helpers.s3_helper import S3Helper
from sync_processor_registry.processor_registry import ProcessorRegistry
from sync_processors.base_processor import BaseProcessor

logger = LoggerHelper(__name__).get_logger()


@ProcessorRegistry.register("s3_upload")
class S3UploadProcessor(BaseProcessor):
    def __init__(self):
        # Initialize with required bucket if needed
        self.s3_helper = S3Helper("knowlio-content-bucket")  # You may want to make this configurable
        
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
    def _generate_presigned_upload_url(self, payload: Dict) -> Dict[str, Any]:
        """
        Generate a presigned URL for direct file upload to S3.
        
        Args:
            payload: Dict with key, content_type (optional), expires_in (optional)
            
        Returns:
            Dict with presigned URL
        """
        require_keys(payload, ["key"])
        key = payload["key"]
        content_type = payload.get("content_type", "application/octet-stream")
        expires_in = int(payload.get("expires_in", 3600))
        
        url = self.s3_helper.generate_presigned_upload_url(
            key=key,
            content_type=content_type,
            expires_in=expires_in
        )
        
        return {"url": url, "key": key}

    def _generate_presigned_download_url(self, payload: Dict) -> Dict[str, Any]:
        """
        Generate a presigned URL for file download from S3.
        
        Args:
            payload: Dict with key, expires_in (optional)
            
        Returns:
            Dict with presigned URL
        """
        require_keys(payload, ["key"])
        key = payload["key"]
        expires_in = int(payload.get("expires_in", 3600))
        
        url = self.s3_helper.generate_presigned_download_url(
            key=key,
            expires_in=expires_in
        )
        
        return {"url": url, "key": key}

    # Multipart upload methods
    def _initiate_multipart_upload(self, payload: Dict) -> Dict[str, Any]:
        """
        Initiate a multipart upload process.
        
        Args:
            payload: Dict with key, content_type (optional)
            
        Returns:
            Dict with upload_id and other details
        """
        require_keys(payload, ["key"])
        key = payload["key"]
        content_type = payload.get("content_type", "application/octet-stream")
        
        result = self.s3_helper.initiate_multipart_upload(
            key=key,
            content_type=content_type
        )
        
        return result

    def _generate_presigned_part_upload_url(self, payload: Dict) -> Dict[str, Any]:
        """
        Generate a presigned URL for uploading a specific part of a multipart upload.
        
        Args:
            payload: Dict with key, upload_id, part_number, expires_in (optional)
            
        Returns:
            Dict with presigned URL and part details
        """
        require_keys(payload, ["key", "upload_id", "part_number"])
        key = payload["key"]
        upload_id = payload["upload_id"]
        part_number = int(payload["part_number"])
        expires_in = int(payload.get("expires_in", 3600))
        
        result = self.s3_helper.generate_presigned_part_upload_url(
            key=key,
            upload_id=upload_id,
            part_number=part_number,
            expires_in=expires_in
        )
        
        return result

    def _complete_multipart_upload(self, payload: Dict) -> Dict[str, Any]:
        """
        Complete a multipart upload after all parts have been uploaded.
        
        Args:
            payload: Dict with key, upload_id, parts (list of dicts with PartNumber and ETag)
            
        Returns:
            Dict with details of the completed upload
        """
        require_keys(payload, ["key", "upload_id", "parts"])
        key = payload["key"]
        upload_id = payload["upload_id"]
        parts = payload["parts"]
        
        # Validate parts format
        if not isinstance(parts, list) or not all(isinstance(p, dict) and 'PartNumber' in p and 'ETag' in p for p in parts):
            raise ValueError("Parts must be a list of dicts with PartNumber and ETag")
        
        result = self.s3_helper.complete_multipart_upload(
            key=key,
            upload_id=upload_id,
            parts=parts
        )
        
        return result

    def _abort_multipart_upload(self, payload: Dict) -> Dict[str, Any]:
        """
        Abort a multipart upload and remove any uploaded parts.
        
        Args:
            payload: Dict with key, upload_id
            
        Returns:
            Dict with status of the abort operation
        """
        require_keys(payload, ["key", "upload_id"])
        key = payload["key"]
        upload_id = payload["upload_id"]
        
        result = self.s3_helper.abort_multipart_upload(
            key=key,
            upload_id=upload_id
        )
        
        return result

    def _list_parts(self, payload: Dict) -> Dict[str, Any]:
        """
        List all parts that have been uploaded for a specific multipart upload.
        
        Args:
            payload: Dict with key, upload_id
            
        Returns:
            Dict with details of all uploaded parts
        """
        require_keys(payload, ["key", "upload_id"])
        key = payload["key"]
        upload_id = payload["upload_id"]
        
        result = self.s3_helper.list_parts(
            key=key,
            upload_id=upload_id
        )
        
        return result
