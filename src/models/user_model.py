
from datetime import datetime
from typing import Dict, Optional
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
        
        # AI Training consent fields
        self.ai_training_consent: bool = user_data.get("ai_training_consent", False)
        self.ai_training_consent_date: Optional[str] = user_data.get("ai_training_consent_date")
        self.ai_training_agreement_version: Optional[str] = user_data.get("ai_training_agreement_version")
        
        # AI Reference consent fields
        self.ai_reference_consent: bool = user_data.get("ai_reference_consent", False)
        self.ai_reference_consent_date: Optional[str] = user_data.get("ai_reference_consent_date")
        
        # AI Marketplace discoverability consent fields
        self.ai_marketplace_consent: bool = user_data.get("ai_marketplace_consent", False)
        self.ai_marketplace_consent_date: Optional[str] = user_data.get("ai_marketplace_consent_date")
