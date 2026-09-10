import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.config import settings
from app.core.audit_chain import AuditChainService, AuditBlockModel
from app.models.schemas import (
    EmployeeModel,
    AccessGrantModel,
    OnboardRequest,
    OffboardRequest,
    EmergencyKillSwitchRequest
)
from app.connectors.github_connector import GitHubConnector
from app.connectors.slack_connector import SlackConnector
from app.connectors.aws_iam_connector import AwsIamConnector

logger = logging.getLogger(__name__)

class IdentityLifecycleService:
    """
    Core orchestrator for role-based provisioning, multi-SaaS synchronization,
    tamper-evident audit ledger hashing, and emergency kill-switch revocation.
    """

    def __init__(self):
        self.github = GitHubConnector()
        self.slack = SlackConnector()
        self.aws = AwsIamConnector()

    async def _append_audit_block(
        self,
        db: AsyncSession,
        action: str,
        target_user_id: str,
        target_email: str,
        actor: str,
        details: Dict[str, Any]
    ) -> AuditBlockModel:
        """Helper to create and link the next cryptographic block in the audit chain."""
        # Find latest block
        latest_query = select(AuditBlockModel).order_by(desc(AuditBlockModel.index)).limit(1)
        res = await db.execute(latest_query)
        latest_block = res.scalars().first()

        next_index = (latest_block.index + 1) if latest_block else 0
        prev_hash = latest_block.block_hash if latest_block else AuditChainService.GENESIS_PREV_HASH
        
        now = datetime.now(timezone.utc)
        time_str = AuditChainService.format_timestamp(now)
        details_str = json.dumps(details, default=str)

        block_hash = AuditChainService.calculate_hash(
            index=next_index,
            timestamp_str=time_str,
            action=action,
            target_user_id=target_user_id,
            target_email=target_email,
            actor=actor,
            details_str=details_str,
            previous_hash=prev_hash
        )

        block = AuditBlockModel(
            index=next_index,
            timestamp=now,
            action=action,
            target_user_id=target_user_id,
            target_email=target_email,
            actor=actor,
            details=details_str,
            previous_hash=prev_hash,
            block_hash=block_hash
        )

        db.add(block)
        await db.flush()
        return block

    async def onboard_employee(
        self,
        payload: OnboardRequest,
        db: AsyncSession
    ) -> EmployeeModel:
        """
        Provisions a new hire across GitHub, Slack, and AWS IAM based on their RBAC role profile.
        """
        # Check if email already exists
        existing_query = select(EmployeeModel).where(EmployeeModel.email == payload.email)
        existing = (await db.execute(existing_query)).scalars().first()
        if existing and existing.status == "ACTIVE":
            raise ValueError(f"Active employee with email {payload.email} already exists.")

        role_cfg = settings.ROLE_PROFILES.get(payload.role, {
            "github_teams": [],
            "github_permission": "pull",
            "slack_channels": ["#general"],
            "aws_roles": []
        })

        employee_id = str(uuid.uuid4())
        iam_user = payload.email.split("@")[0].replace(".", "-")

        employee = EmployeeModel(
            id=employee_id,
            full_name=payload.full_name,
            email=payload.email,
            department=payload.department,
            role=payload.role,
            github_username=payload.github_username,
            slack_handle=payload.slack_handle,
            aws_iam_user=iam_user,
            status="ACTIVE",
            provisioned_by=payload.initiator
        )

        user_dict = {
            "full_name": payload.full_name,
            "email": payload.email,
            "role": payload.role,
            "github_username": payload.github_username,
            "slack_handle": payload.slack_handle
        }

        # 1. Provision across SaaS platforms
        gh_grants = await self.github.provision_access(user_dict, role_cfg)
        slack_grants = await self.slack.provision_access(user_dict, role_cfg)
        aws_grants = await self.aws.provision_access(user_dict, role_cfg)

        all_grants = gh_grants + slack_grants + aws_grants

        # 2. Record access grants in DB
        for g in all_grants:
            grant_model = AccessGrantModel(
                employee_id=employee_id,
                platform=g["platform"],
                resource_name=g["resource_name"],
                access_level=g["access_level"],
                is_active=True
            )
            employee.access_grants.append(grant_model)

        db.add(employee)
        await db.flush()

        # 3. Add cryptographic audit block
        await self._append_audit_block(
            db=db,
            action="ONBOARD_PROVISION",
            target_user_id=employee_id,
            target_email=payload.email,
            actor=payload.initiator,
            details={
                "role": payload.role,
                "department": payload.department,
                "grants_count": len(all_grants),
                "platforms": ["GITHUB", "SLACK", "AWS_IAM"]
            }
        )

        await db.commit()
        await db.refresh(employee)
        return employee

    async def emergency_killswitch(
        self,
        employee_id: str,
        payload: EmergencyKillSwitchRequest,
        db: AsyncSession
    ) -> EmployeeModel:
        """
        1-Click Emergency Offboarding / Kill-Switch. Instantly and simultaneously revokes
        all GitHub org access, terminates Slack sessions, purges AWS STS keys, and records a sealed audit entry.
        """
        query = select(EmployeeModel).where(EmployeeModel.id == employee_id)
        employee = (await db.execute(query)).scalars().first()
        if not employee:
            raise ValueError(f"Employee ID {employee_id} not found.")

        user_dict = {
            "full_name": employee.full_name,
            "email": employee.email,
            "github_username": employee.github_username,
            "slack_handle": employee.slack_handle
        }

        # 1. Execute instantaneous revocation across all SaaS connectors
        gh_revocations = await self.github.revoke_all_access(user_dict)
        slack_revocations = await self.slack.revoke_all_access(user_dict)
        aws_revocations = await self.aws.revoke_all_access(user_dict)

        all_revocations = gh_revocations + slack_revocations + aws_revocations

        # 2. Update employee status & access grants
        now = datetime.now(timezone.utc)
        employee.status = "KILLSWITCH_TERMINATED"
        employee.offboarded_at = now
        employee.offboarded_by = f"{payload.initiator} [{payload.authorization_code}]"

        for grant in employee.access_grants:
            grant.is_active = False
            grant.revoked_at = now

        # 3. Seal action into cryptographic audit chain
        await self._append_audit_block(
            db=db,
            action="EMERGENCY_KILLSWITCH",
            target_user_id=employee.id,
            target_email=employee.email,
            actor=payload.initiator,
            details={
                "reason": payload.reason,
                "auth_code": payload.authorization_code,
                "revoked_resources": all_revocations
            }
        )

        await db.commit()
        await db.refresh(employee)
        return employee

    async def offboard_employee(
        self,
        employee_id: str,
        payload: OffboardRequest,
        db: AsyncSession
    ) -> EmployeeModel:
        """Standard graceful offboarding."""
        kill_req = EmergencyKillSwitchRequest(
            reason=payload.reason,
            initiator=payload.initiator,
            authorization_code="STD-OFFBOARD"
        )
        emp = await self.emergency_killswitch(employee_id, kill_req, db)
        emp.status = "OFFBOARDED"
        await db.commit()
        await db.refresh(emp)
        return emp
