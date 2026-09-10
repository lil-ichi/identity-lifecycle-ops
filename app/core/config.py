from pydantic_settings import BaseSettings
from typing import Dict, List, Any, Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "IdentityLifecycle Ops"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    DATABASE_URL: str = "sqlite+aiosqlite:///./identities.db"
    
    # External SaaS API Keys / Tokens (Optional - operates with functional live simulation if unconfigured)
    GITHUB_ORG_TOKEN: Optional[str] = None
    GITHUB_ORG_NAME: str = "enterprise-corp"
    
    SLACK_BOT_TOKEN: Optional[str] = None
    SLACK_WELCOME_CHANNEL: str = "C_GENERAL"
    
    AWS_REGION: str = "us-east-1"
    AWS_ACCOUNT_ID: str = "123456789012"
    
    # Pre-configured RBAC Matrix (Least-Privilege Templates)
    ROLE_PROFILES: Dict[str, Dict[str, Any]] = {
        "SOFTWARE_ENGINEER": {
            "github_teams": ["backend-devs", "code-reviewers"],
            "github_permission": "push",
            "slack_channels": ["#dev-announcements", "#engineering", "#frontend-backend"],
            "aws_roles": ["arn:aws:iam::123456789012:role/DeveloperSandboxAccess"]
        },
        "DEVOPS_ENGINEER": {
            "github_teams": ["infra-core", "sre-oncall"],
            "github_permission": "admin",
            "slack_channels": ["#infra-alerts", "#engineering", "#security-ops"],
            "aws_roles": ["arn:aws:iam::123456789012:role/SREPlatformAdmin"]
        },
        "PRODUCT_MANAGER": {
            "github_teams": ["product-specs"],
            "github_permission": "triage",
            "slack_channels": ["#product-roadmap", "#general", "#customer-feedback"],
            "aws_roles": ["arn:aws:iam::123456789012:role/DataAnalyticsReadOnly"]
        },
        "FINANCE_ANALYST": {
            "github_teams": [],
            "github_permission": "none",
            "slack_channels": ["#finance-ops", "#general", "#billing-alerts"],
            "aws_roles": ["arn:aws:iam::123456789012:role/BillingAuditor"]
        }
    }

    model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()
