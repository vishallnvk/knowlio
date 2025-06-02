from datetime import datetime
from typing import Dict, Optional
import uuid


class UsageLogModel:
    def __init__(self, log_data: Dict):
        self.log_id: str = str(uuid.uuid4())
        self.content_id: str = log_data["content_id"]
        self.consumer_id: str = log_data["consumer_id"]
        self.access_time: str = datetime.utcnow().isoformat()
        self.ip_address: str = log_data.get("ip_address", "")
        self.user_agent: str = log_data.get("user_agent", "")
        self.publisher_id: str = log_data["publisher_id"]
        self.access_type: str = log_data.get("access_type", "VIEW")
        self.region: str = log_data.get("region", "")
        self.metadata: Dict = log_data.get("metadata", {})
