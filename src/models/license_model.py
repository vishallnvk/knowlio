from datetime import datetime
from typing import Dict
import uuid


class LicenseModel:
    def __init__(self, license_data: Dict):
        self.license_id: str = str(uuid.uuid4())
        self.content_id: str = license_data["content_id"]
        self.publisher_id: str = license_data["publisher_id"]
        self.consumer_id: str = license_data["consumer_id"]
        self.license_terms: Dict = license_data["license_terms"]
        self.status: str = "ACTIVE"
        self.created_at: str = datetime.utcnow().isoformat()
        self.revoked_at: str = None
        self.version: str = license_data.get("version", "v1.0")
