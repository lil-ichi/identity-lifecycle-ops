from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.core.config import settings
from app.core.audit_chain import AuditChainService, AuditBlockModel
from app.models.schemas import (
    EmployeeModel,
    EmployeeResponse,
    OnboardRequest,
    OffboardRequest,
    EmergencyKillSwitchRequest,
    AuditBlockResponse
)
from app.services.lifecycle import IdentityLifecycleService

router = APIRouter(prefix="/identities", tags=["Identity Lifecycle"])
lifecycle_service = IdentityLifecycleService()

@router.post("/onboard", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def onboard_new_employee(
    payload: OnboardRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Automates 1-Click Role-Based Provisioning across GitHub, Slack, and AWS IAM.
    Creates cryptographically chained SOC2 audit ledger block.
    """
    try:
        employee = await lifecycle_service.onboard_employee(payload, db)
        return employee
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Onboarding orchestration failed: {str(e)}")


@router.get("/employees", response_model=List[EmployeeResponse])
async def list_employees(
    status_filter: Optional[str] = Query(None, description="Filter by: ACTIVE, OFFBOARDED, KILLSWITCH_TERMINATED"),
    search: Optional[str] = Query(None, description="Search by name, email, or department"),
    db: AsyncSession = Depends(get_db)
):
    """Lists all managed company identities with active resource entitlements."""
    query = select(EmployeeModel).order_by(desc(EmployeeModel.created_at))
    if status_filter:
        query = query.where(EmployeeModel.status == status_filter.upper())
    if search:
        query = query.where(
            (EmployeeModel.full_name.ilike(f"%{search}%")) |
            (EmployeeModel.email.ilike(f"%{search}%")) |
            (EmployeeModel.department.ilike(f"%{search}%"))
        )
    res = await db.execute(query)
    return res.scalars().all()


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee_details(
    employee_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Returns complete identity profile, active permissions graph, and metadata."""
    query = select(EmployeeModel).where(EmployeeModel.id == employee_id)
    emp = (await db.execute(query)).scalars().first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee identity not found")
    return emp


@router.post("/employees/{employee_id}/offboard", response_model=EmployeeResponse)
async def offboard_employee_standard(
    employee_id: str,
    payload: OffboardRequest,
    db: AsyncSession = Depends(get_db)
):
    """Graceful offboarding: revokes SaaS accounts and archives profile."""
    try:
        emp = await lifecycle_service.offboard_employee(employee_id, payload, db)
        return emp
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/employees/{employee_id}/killswitch", response_model=EmployeeResponse)
async def trigger_emergency_killswitch_api(
    employee_id: str,
    payload: EmergencyKillSwitchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    🚨 1-CLICK EMERGENCY KILL-SWITCH
    Instantly purges all SaaS tokens, drops GitHub org access, suspends Slack,
    terminates active AWS STS sessions in parallel, and cryptographically records event.
    """
    try:
        emp = await lifecycle_service.emergency_killswitch(employee_id, payload, db)
        return emp
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/audit/chain", response_model=List[AuditBlockResponse])
async def get_audit_ledger(db: AsyncSession = Depends(get_db)):
    """Retrieves full cryptographic audit chain for compliance verification."""
    query = select(AuditBlockModel).order_by(AuditBlockModel.index.asc())
    blocks = (await db.execute(query)).scalars().all()
    return blocks


@router.get("/audit/verify")
async def verify_audit_chain_integrity(db: AsyncSession = Depends(get_db)):
    """
    Walks the SHA-256 blockchain-style ledger from Genesis block to current block
    to mathematically verify that zero audit records have been altered or pruned.
    """
    query = select(AuditBlockModel).order_by(AuditBlockModel.index.asc())
    blocks = (await db.execute(query)).scalars().all()
    verification_result = AuditChainService.verify_integrity(blocks)
    return verification_result


@router.get("/roles")
async def list_available_roles():
    """Returns configured RBAC permission matrices."""
    return settings.ROLE_PROFILES
