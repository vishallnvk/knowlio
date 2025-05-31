
from datetime import datetime
from typing import Dict
import uuid


class UserModel:
    def __init__(self, user_data: Dict):
        self.user_id: str = str(uuid.uuid4())
        self.email: str = user_data["email"]
        self.role: str = user_data["role"]
        self.name: str = user_data.get("name", "")
        self.organization: str = user_data.get("organization", "")
        self.auth_provider: str = user_data.get("auth_provider", "COGNITO")
        self.created_at: str = datetime.utcnow().isoformat()
        self.metadata: Dict = user_data.get("metadata", {})