import boto3
import json
import botocore.exceptions
from typing import Dict, List, Optional, Any

from helpers.common_helper.logger_helper import LoggerHelper
from helpers.common_helper.common_helper import Retry

logger = LoggerHelper(__name__).get_logger()

class S3Helper:
    def __init__(self, bucket_name: str = None):
        self.s3 = boto3.client("s3")
        self.bucket_name = bucket_name or self._get_default_bucket()

    def _get_default_bucket(self) -> str:
        # You can enhance this later to use env vars or config
        raise ValueError("Bucket name must be provided to S3Helper.")

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def generate_presigned_upload_url(
        self,
        key: str,
        content_type: str = "application/octet-stream",
        expires_in: int = 3600
    ) -> str:
        logger.info(f"Generating presigned upload URL for key={key}")
        return self.s3.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': self.bucket_name,
                'Key': key,
                'ContentType': content_type
            },
            ExpiresIn=expires_in
        )

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def generate_presigned_download_url(
        self,
        key: str,
        expires_in: int = 3600
    ) -> str:
        logger.info(f"Generating presigned download URL for key={key}")
        return self.s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': self.bucket_name,
                'Key': key
            },
            ExpiresIn=expires_in
        )

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def upload_file(self, file_path: str, key: str) -> None:
        logger.info(f"Uploading file to s3://{self.bucket_name}/{key}")
        self.s3.upload_file(file_path, self.bucket_name, key)

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def download_file(self, key: str, download_path: str) -> None:
        logger.info(f"Downloading s3://{self.bucket_name}/{key} to {download_path}")
        self.s3.download_file(self.bucket_name, key, download_path)

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def upload_data_as_json(self, data: str, key: str) -> str:
        """Upload string data directly to S3 as JSON/JSONL format"""
        logger.info(f"Uploading data to s3://{self.bucket_name}/{key}")
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=data.encode('utf-8'),
            ContentType='application/json'
        )
        return f"s3://{self.bucket_name}/{key}"

    def generate_export_key(self, prefix: str, date_str: str, timestamp: str, format_type: str = "jsonl") -> str:
        """Generate standardized S3 key for exports"""
        return f"{prefix}/{date_str}/{prefix}_{timestamp}.{format_type}"

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def list_objects(self, prefix: str = "") -> list:
        """List objects in the bucket with optional prefix filter"""
        logger.info(f"Listing objects in s3://{self.bucket_name} with prefix={prefix}")
        response = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
        return response.get('Contents', [])

    # Multipart Upload Methods
    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def initiate_multipart_upload(self, key: str, content_type: str = "application/octet-stream") -> Dict[str, Any]:
        """
        Initiate a multipart upload process and return upload ID.
        
        Args:
            key: The S3 key where the file will be stored
            content_type: The content type of the file
            
        Returns:
            Dict containing the upload_id and other details
        """
        logger.info(f"Initiating multipart upload for key={key}")
        response = self.s3.create_multipart_upload(
            Bucket=self.bucket_name,
            Key=key,
            ContentType=content_type
        )
        
        return {
            "upload_id": response['UploadId'],
            "key": key,
            "bucket": self.bucket_name
        }

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def generate_presigned_part_upload_url(
        self, 
        key: str, 
        upload_id: str, 
        part_number: int,
        expires_in: int = 3600
    ) -> Dict[str, Any]:
        """
        Generate a presigned URL for uploading a specific part of a multipart upload.
        
        Args:
            key: The S3 key where the file is being stored
            upload_id: The ID of the multipart upload
            part_number: The part number (1-10000)
            expires_in: URL expiration time in seconds
            
        Returns:
            Dict containing the presigned URL and other details
        """
        logger.info(f"Generating presigned URL for part {part_number} of upload_id={upload_id}, key={key}")
        
        url = self.s3.generate_presigned_url(
            ClientMethod='upload_part',
            Params={
                'Bucket': self.bucket_name,
                'Key': key,
                'UploadId': upload_id,
                'PartNumber': part_number
            },
            ExpiresIn=expires_in
        )
        
        return {
            "url": url,
            "part_number": part_number,
            "key": key,
            "upload_id": upload_id
        }

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def complete_multipart_upload(
        self, 
        key: str, 
        upload_id: str, 
        parts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Complete a multipart upload after all parts have been uploaded.
        
        Args:
            key: The S3 key where the file is being stored
            upload_id: The ID of the multipart upload
            parts: List of dicts with 'PartNumber' and 'ETag' for each uploaded part
            
        Returns:
            Dict containing the details of the completed upload
        """
        logger.info(f"Completing multipart upload for upload_id={upload_id}, key={key} with {len(parts)} parts")
        
        # Parts must be in the correct format and sorted by part number
        formatted_parts = [{'PartNumber': p['PartNumber'], 'ETag': p['ETag']} for p in parts]
        formatted_parts.sort(key=lambda x: x['PartNumber'])
        
        response = self.s3.complete_multipart_upload(
            Bucket=self.bucket_name,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={'Parts': formatted_parts}
        )
        
        return {
            "location": response['Location'],
            "bucket": self.bucket_name,
            "key": key,
            "etag": response['ETag']
        }

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def abort_multipart_upload(self, key: str, upload_id: str) -> Dict[str, Any]:
        """
        Abort a multipart upload process and remove any partially uploaded parts.
        
        Args:
            key: The S3 key where the file was being stored
            upload_id: The ID of the multipart upload
            
        Returns:
            Dict indicating the result of the abort operation
        """
        logger.info(f"Aborting multipart upload for upload_id={upload_id}, key={key}")
        
        self.s3.abort_multipart_upload(
            Bucket=self.bucket_name,
            Key=key,
            UploadId=upload_id
        )
        
        return {
            "status": "aborted",
            "bucket": self.bucket_name,
            "key": key,
            "upload_id": upload_id
        }

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def list_parts(self, key: str, upload_id: str) -> Dict[str, Any]:
        """
        List all parts that have been uploaded for a specific multipart upload.
        
        Args:
            key: The S3 key where the file is being stored
            upload_id: The ID of the multipart upload
            
        Returns:
            Dict containing details of all uploaded parts
        """
        logger.info(f"Listing parts for upload_id={upload_id}, key={key}")
        
        response = self.s3.list_parts(
            Bucket=self.bucket_name,
            Key=key,
            UploadId=upload_id
        )
        
        parts = []
        if 'Parts' in response:
            parts = [{
                'PartNumber': part['PartNumber'],
                'ETag': part['ETag'],
                'Size': part['Size'],
                'LastModified': part['LastModified'].isoformat() if hasattr(part['LastModified'], 'isoformat') else str(part['LastModified'])
            } for part in response['Parts']]
        
        return {
            "parts": parts,
            "bucket": self.bucket_name,
            "key": key,
            "upload_id": upload_id,
            "part_count": len(parts)
        }
