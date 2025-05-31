from typing import Dict

from helpers.common_helper.common_helper import require_keys
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.app_logic_helpers.user_helper import UserHelper
from sync_processor_registry.processor_registry import ProcessorRegistry
from sync_processors.base_processor import BaseProcessor

logger = LoggerHelper(__name__).get_logger()


@ProcessorRegistry.register("user")
class UserProcessor(BaseProcessor):
    def __init__(self):
        self.helper = UserHelper()
        super().__init__({
            "register_user": self._register_user,
            "get_user_profile": self._get_user_profile,
            "update_user_profile": self._update_user_profile,
            "list_users_by_role": self._list_users_by_role,
        })

    def _register_user(self, payload: Dict) -> Dict:
        require_keys(payload, ["email", "role"])
        return self.helper.register_user(payload)

    def _get_user_profile(self, payload: Dict) -> Dict:
        require_keys(payload, ["user_id"])
        return self.helper.get_user_profile(payload["user_id"])

    def _update_user_profile(self, payload: Dict) -> Dict:
        require_keys(payload, ["user_id", "updates"])
        return self.helper.update_user_profile(payload["user_id"], payload["updates"])

    def _list_users_by_role(self, payload: Dict) -> Dict:
        require_keys(payload, ["role"])
        return {"users": self.helper.list_users_by_role(payload["role"])}