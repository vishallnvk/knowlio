import boto3

from helpers.common_helper.logger_helper import LoggerHelper

logger = LoggerHelper(__name__).get_logger()

class S3Helper:
    def __init__(self, bucket_name: str = None):
        self.s3 = boto3.client("s3")
        self.bucket_name = bucket_name or self._get_default_bucket()

    def _get_default_bucket(self) -> str:
        # You can enhance this later to use env vars or config
        raise ValueError("Bucket name must be provided to S3Helper.")

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

    def upload_file(self, file_path: str, key: str) -> None:
        logger.info(f"Uploading file to s3://{self.bucket_name}/{key}")
        self.s3.upload_file(file_path, self.bucket_name, key)

    def download_file(self, key: str, download_path: str) -> None:
        logger.info(f"Downloading s3://{self.bucket_name}/{key} to {download_path}")
        self.s3.download_file(self.bucket_name, key, download_path)