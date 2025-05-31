import uuid
from typing import Optional, Dict, List

from helpers.aws_service_helpers.dynamodb_helper import DynamoDBHelper
from helpers.common_helper.logger_helper import LoggerHelper
from models.user_model import UserModel

logger = LoggerHelper(__name__).get_logger()

USERS_TABLE = "users"

class UserHelper:
    def __init__(self):
        self.db = DynamoDBHelper(table_name=USERS_TABLE)

    def register_user(self, user_data: Dict) -> Dict:
        user_id = str(uuid.uuid4())
        user_item = UserModel(user_data).__dict__

        logger.info("Registering user: %s", user_item)
        self.db.put_item(user_item)
        return {"message": "User registered successfully", "user_id": user_id}

    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        logger.info("Fetching user profile for user_id: %s", user_id)
        return self.db.get_item({"user_id": user_id})

    def update_user_profile(self, user_id: str, updates: Dict) -> Dict:
        logger.info("Updating user profile for user_id: %s with updates: %s", user_id, updates)
        return self.db.update_item("user_id", user_id, updates)

    def list_users_by_role(self, role: str) -> List[Dict]:
        logger.info("Listing users with role: %s", role)
        return self.db.query_items("role", role)
