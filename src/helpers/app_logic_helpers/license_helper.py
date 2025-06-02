import uuid
from datetime import datetime
from typing import Optional, Dict, List

from helpers.aws_service_helpers.dynamodb_helper import DynamoDBHelper
from helpers.common_helper.logger_helper import LoggerHelper
from models.license_model import LicenseModel

logger = LoggerHelper(__name__).get_logger()

LICENSES_TABLE = "licenses"

class LicenseHelper:
    def __init__(self):
        self.db = DynamoDBHelper(table_name=LICENSES_TABLE)

    def create_license(self, license_data: Dict) -> Dict:
        license_item = LicenseModel(license_data).__dict__

        logger.info("Creating license: %s", license_item)
        self.db.put_item(license_item)
        return {"message": "License created successfully", "license_id": license_item["license_id"]}

    def get_license(self, license_id: str) -> Optional[Dict]:
        logger.info("Fetching license for license_id: %s", license_id)
        return self.db.get_item({"license_id": license_id})

    def list_licenses_by_consumer(self, consumer_id: str) -> List[Dict]:
        logger.info("Listing licenses for consumer_id: %s", consumer_id)
        return self.db.query_items("consumer_id", consumer_id)

    def list_licenses_by_content(self, content_id: str) -> List[Dict]:
        logger.info("Listing licenses for content_id: %s", content_id)
        return self.db.query_items("content_id", content_id)

    def revoke_license(self, license_id: str) -> Dict:
        logger.info("Revoking license for license_id: %s", license_id)
        updates = {
            "status": "REVOKED",
            "revoked_at": datetime.utcnow().isoformat()
        }
        return self.db.update_item("license_id", license_id, updates)
