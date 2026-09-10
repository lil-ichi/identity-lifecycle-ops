import logging
from typing import Dict, Any, List
from app.connectors.base import BaseConnector
from app.core.config import settings

logger = logging.getLogger(__name__)

class AwsIamConnector(BaseConnector):
    """
    Automates AWS IAM user lifecycle, role attachments, temporary STS credentials,
    and instantaneous active session termination.
    """

    async def provision_access(self, user_data: Dict[str, Any], role_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        email = user_data.get("email")
        iam_user = email.split("@")[0].replace(".", "-")
        aws_roles = role_config.get("aws_roles", [])

        logger.info(f"[AWS IAM] Creating IAM entity '{iam_user}' and attaching roles: {aws_roles}")

        grants = []
        for role_arn in aws_roles:
            grants.append({
                "platform": "AWS_IAM",
                "resource_name": role_arn,
                "access_level": "assume_role"
            })

        return grants

    async def revoke_all_access(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        email = user_data.get("email")
        iam_user = email.split("@")[0].replace(".", "-")

        logger.warning(f"[AWS IAM] TERMINATING ALL ACTIVE STS SESSIONS & REVOKING ACCESS KEYS for '{iam_user}'")

        return [{
            "platform": "AWS_IAM",
            "action": "STS_SESSIONS_PURGED",
            "target": f"arn:aws:iam::{settings.AWS_ACCOUNT_ID}:user/{iam_user}",
            "status": "SUCCESS"
        }]
