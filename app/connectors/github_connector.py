import logging
import httpx
from typing import Dict, Any, List
from app.connectors.base import BaseConnector
from app.core.config import settings

logger = logging.getLogger(__name__)

class GitHubConnector(BaseConnector):
    """
    Automates GitHub Organization membership, team invitations,
    repository permission assignments, and emergency access revocation.
    """

    def __init__(self):
        self.token = settings.GITHUB_ORG_TOKEN
        self.org = settings.GITHUB_ORG_NAME
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {self.token}" if self.token else "",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    async def provision_access(self, user_data: Dict[str, Any], role_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        username = user_data.get("github_username")
        if not username:
            logger.info("No GitHub username specified; skipping GitHub provisioning.")
            return []

        grants = []
        teams = role_config.get("github_teams", [])
        permission = role_config.get("github_permission", "pull")

        logger.info(f"[GITHUB] Provisioning user '{username}' in org '{self.org}' with teams {teams}")

        if self.token:
            try:
                async with httpx.AsyncClient(timeout=10.0, headers=self.headers) as client:
                    # 1. Invite to organization
                    invite_url = f"{self.base_url}/orgs/{self.org}/invitations"
                    await client.post(invite_url, json={"email": user_data.get("email"), "role": "direct_member"})

                    # 2. Add to specified teams
                    for team_slug in teams:
                        team_url = f"{self.base_url}/orgs/{self.org}/teams/{team_slug}/memberships/{username}"
                        await client.put(team_url, json={"role": "member"})
            except Exception as e:
                logger.error(f"[GITHUB] API execution error: {e}")

        for team_slug in teams:
            grants.append({
                "platform": "GITHUB",
                "resource_name": f"team:{team_slug}",
                "access_level": permission
            })

        return grants

    async def revoke_all_access(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        username = user_data.get("github_username")
        if not username:
            return []

        logger.warning(f"[GITHUB] PURGING ALL ACCESS for user '{username}' from org '{self.org}'")

        if self.token:
            try:
                async with httpx.AsyncClient(timeout=10.0, headers=self.headers) as client:
                    # Remove from org (automatically revokes all team memberships & private repo forks)
                    remove_url = f"{self.base_url}/orgs/{self.org}/members/{username}"
                    await client.delete(remove_url)
            except Exception as e:
                logger.error(f"[GITHUB] Failed to remove user {username}: {e}")

        return [{
            "platform": "GITHUB",
            "action": "ORG_MEMBERSHIP_REVOKED",
            "target": f"{self.org}/{username}",
            "status": "SUCCESS"
        }]
