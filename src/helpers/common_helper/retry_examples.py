"""
Examples demonstrating how to use the Retry decorator with various AWS services.
"""

import time
import random
import boto3
import botocore.exceptions
import urllib.request
import urllib.error
import json
from typing import Dict, Any, List

from helpers.common_helper.common_helper import Retry
from helpers.common_helper.logger_helper import LoggerHelper

logger = LoggerHelper(__name__).get_logger()


# Example 1: Simple function with retry
@Retry(max_attempts=3, initial_wait=0.5, exceptions=ValueError)
def example_function_with_retry(value: int) -> int:
    """Example function that might fail and will retry"""
    # Simulate random failures
    if random.random() < 0.7:  # 70% chance of failure on first try
        logger.warning("Simulating a failure")
        raise ValueError("Simulated failure")
    
    logger.info("Function succeeded")
    return value * 2


# Example 2: DynamoDB operations with retry
class DynamoDBExample:
    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)
    
    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError])
    def get_item_with_retry(self, key: str) -> Dict:
        """Get item from DynamoDB with retry logic"""
        logger.info(f"Getting item with key: {key}")
        response = self.table.get_item(Key={"id": key})
        return response.get("Item")


# Example 3: External API calls with retry
class APIExample:
    @Retry(max_attempts=3, initial_wait=2.0, exceptions=[urllib.error.URLError, json.JSONDecodeError])
    def fetch_data(self, url: str) -> Dict:
        """Fetch data from an external API with retry logic"""
        logger.info(f"Fetching data from: {url}")
        
        with urllib.request.urlopen(url) as response:
            response_data = response.read().decode('utf-8')
            return json.loads(response_data)


# Example 4: S3 operations with retry and multiple exception types
class S3Example:
    def __init__(self, bucket_name: str):
        self.s3 = boto3.client("s3")
        self.bucket_name = bucket_name
    
    @Retry(
        max_attempts=3,
        initial_wait=1.0,
        backoff_factor=2.0,
        exceptions=[
            botocore.exceptions.ClientError,
            botocore.exceptions.BotoCoreError,
            ConnectionError
        ]
    )
    def upload_file_with_retry(self, file_path: str, key: str) -> None:
        """Upload file to S3 with retry logic"""
        logger.info(f"Uploading file to s3://{self.bucket_name}/{key}")
        self.s3.upload_file(file_path, self.bucket_name, key)


def demonstrate_retry():
    """Run examples to demonstrate the retry decorator"""
    # Example 1: Simple function with retry
    print("\n=== Example 1: Simple function with retry ===")
    try:
        result = example_function_with_retry(10)
        print(f"Result: {result}")
    except ValueError as e:
        print(f"Function failed after all retry attempts: {str(e)}")
    
    # Example of a function that's not decorated with Retry
    print("\n=== Comparison: Function without retry ===")
    try:
        # This function will fail immediately without retrying
        if random.random() < 0.7:
            raise ValueError("Immediate failure")
        print("Function succeeded")
    except ValueError as e:
        print(f"Function failed without retrying: {str(e)}")
    
    
if __name__ == "__main__":
    demonstrate_retry()
