import uuid
from typing import Dict, List, Optional

from helpers.aws_service_helpers.dynamodb_helper import DynamoDBHelper
from helpers.common_helper.logger_helper import LoggerHelper
from models.content_model import ContentModel

logger = LoggerHelper(__name__).get_logger()

CONTENT_TABLE = "content"

class ContentHelper:
    def __init__(self):
        self.db = DynamoDBHelper(table_name=CONTENT_TABLE)

    def upload_content_metadata(self, content_data: Dict) -> Dict:
        content_id = str(uuid.uuid4())
        content_item = ContentModel(content_data).__dict__

        logger.info("Uploading content metadata: %s", content_item)
        self.db.put_item(content_item)
        return {"message": "Content metadata uploaded", "content_id": content_id}

    def upload_content_blob(self, content_id: str, file_key: str) -> Dict:
        logger.info("Attaching file key '%s' to content_id: %s", file_key, content_id)
        return self.db.update_item("content_id", content_id, {"file_key": file_key, "status": "ACTIVE"})

    def get_content_details(self, content_id: str) -> Optional[Dict]:
        logger.info("Fetching content details for content_id: %s", content_id)
        return self.db.get_item({"content_id": content_id})

    def update_content_metadata(self, content_id: str, updates: Dict) -> Dict:
        logger.info("Updating content metadata for content_id: %s with: %s", content_id, updates)
        return self.db.update_item("content_id", content_id, updates)

    def list_content_by_publisher(self, publisher_id: str) -> List[Dict]:
        logger.info("Listing content for publisher_id: %s", publisher_id)
        return self.db.query_items("publisher_id", publisher_id)

    def archive_content(self, content_id: str) -> Dict:
        logger.info("Archiving content_id: %s", content_id)
        return self.db.update_item("content_id", content_id, {"status": "ARCHIVED"})