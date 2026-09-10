from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseConnector(ABC):
    """
    Abstract SaaS connector defining standardized onboarding and
    emergency offboarding/revocation hooks.
    """

    @abstractmethod
    async def provision_access(self, user_data: Dict[str, Any], role_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Grants required role-based permissions on target SaaS platform.
        Returns a list of granted resource metadata.
        """
        pass

    @abstractmethod
    async def revoke_all_access(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Immediately purges and revokes all active sessions, tokens, and permissions.
        Returns a list of revoked resource actions.
        """
        pass
