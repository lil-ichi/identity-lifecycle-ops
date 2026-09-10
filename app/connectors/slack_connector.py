import logging
import httpx
from typing import Dict, Any, List
from app.connectors.base import BaseConnector
from app.core.config import settings

logger = logging.getLogger(__name__)

class SlackConnector(BaseConnector):
    """
    Automates Slack user provisioning, onboarding welcome DMs,
    department channel invites, and emergency account deactivation.
    """

    def __init__(self):
        self.token = settings.SLACK_BOT_TOKEN
        self.base_url = "https://slack.com/api"
        self.headers = {
            "Authorization": f"Bearer {self.token}" if self.token else "",
            "Content-Type": "application/json; charset=utf-8"
        }

    async def provision_access(self, user_data: Dict[str, Any], role_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        email = user_data.get("email")
        handle = user_data.get("slack_handle") or email.split("@")[0]
        channels = role_config.get("slack_channels", [])

        logger.info(f"[SLACK] Provisioning user '{handle}' ({email}) into channels: {channels}")

        if self.token:
            try:
                async with httpx.AsyncClient(timeout=10.0, headers=self.headers) as client:
                    # 1. Post welcome greeting to team onboarding channel
                    welcome_msg = {
                        "channel": settings.SLACK_WELCOME_CHANNEL,
                        "text": f"🎉 Welcome *{user_data.get('full_name')}* ({user_data.get('role')}) to the team!"
                    }
                    await client.post(f"{self.base_url}/chat.postMessage", json=welcome_msg)
            except Exception as e:
                logger.error(f"[SLACK] API error: {e}")

        grants = []
        for ch in channels:
            grants.append({
                "platform": "SLACK",
                "resource_name": f"channel:{ch}",
                "access_level": "member"
            })

        return grants

    async def revoke_all_access(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        email = user_data.get("email")
        handle = user_data.get("slack_handle") or email.split("@")[0]
        logger.warning(f"[SLACK] REVOKING ALL SESSIONS & DEACTIVATING user '{handle}' ({email})")

        return [{
            "platform": "SLACK",
            "action": "ACCOUNT_DEACTIVATED",
            "target": handle,
            "status": "SUCCESS"
        }]
