import pytest
import pytest_asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.database import Base
from app.core.audit_chain import AuditChainService, AuditBlockModel
from app.models.schemas import OnboardRequest, EmergencyKillSwitchRequest, EmployeeModel
from app.services.lifecycle import IdentityLifecycleService

# In-memory test DB
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()

@pytest.mark.asyncio
async def test_onboard_employee_rbac_grants(db_session):
    """Verifies automated multi-SaaS provisioning according to role templates."""
    service = IdentityLifecycleService()
    req = OnboardRequest(
        full_name="Alice Vance",
        email="alice.vance@enterprise.io",
        department="Engineering",
        role="SOFTWARE_ENGINEER",
        github_username="alice-vance",
        slack_handle="@alice.vance"
    )

    employee = await service.onboard_employee(req, db_session)

    assert employee.id is not None
    assert employee.status == "ACTIVE"
    assert employee.full_name == "Alice Vance"
    assert len(employee.access_grants) > 0

    # Verify GitHub, Slack, and AWS IAM resources were granted
    platforms = [g.platform for g in employee.access_grants]
    assert "GITHUB" in platforms
    assert "SLACK" in platforms
    assert "AWS_IAM" in platforms

@pytest.mark.asyncio
async def test_emergency_killswitch_revocation(db_session):
    """Verifies that the emergency kill-switch revokes all entitlements in parallel."""
    service = IdentityLifecycleService()
    req = OnboardRequest(
        full_name="Bob Hostile",
        email="bob.hostile@enterprise.io",
        department="DevOps",
        role="DEVOPS_ENGINEER",
        github_username="bob-hostile"
    )

    employee = await service.onboard_employee(req, db_session)
    assert employee.status == "ACTIVE"

    # Trigger 1-Click KillSwitch
    kill_req = EmergencyKillSwitchRequest(
        reason="Security Breach Detected",
        initiator="CISO Office",
        authorization_code="SEC-KILL-991"
    )

    terminated = await service.emergency_killswitch(employee.id, kill_req, db_session)

    assert terminated.status == "KILLSWITCH_TERMINATED"
    assert terminated.offboarded_at is not None
    # All access grants must be inactive
    for grant in terminated.access_grants:
        assert grant.is_active is False
        assert grant.revoked_at is not None

@pytest.mark.asyncio
async def test_cryptographic_audit_chain_verification(db_session):
    """Verifies SHA-256 blockchain integrity and tamper detection."""
    service = IdentityLifecycleService()
    
    # 1. Trigger multiple operations to build chain
    req1 = OnboardRequest(
        full_name="Carol Danvers",
        email="carol@enterprise.io",
        department="Product",
        role="PRODUCT_MANAGER"
    )
    emp = await service.onboard_employee(req1, db_session)

    kill_req = EmergencyKillSwitchRequest(
        reason="Emergency Test",
        initiator="SecOps Officer",
        authorization_code="SEC-TEST-001"
    )
    await service.emergency_killswitch(emp.id, kill_req, db_session)

    # 2. Retrieve blocks and verify integrity
    from sqlalchemy import select
    blocks = (await db_session.execute(select(AuditBlockModel).order_by(AuditBlockModel.index.asc()))).scalars().all()
    assert len(blocks) == 2

    report = AuditChainService.verify_integrity(blocks)
    assert report["valid"] is True
    assert report["total_blocks"] == 2

    # 3. Simulate malicious database tampering on block 0
    blocks[0].details = '{"tampered": true}'
    tamper_report = AuditChainService.verify_integrity(blocks)
    assert tamper_report["valid"] is False
    assert "Hash mismatch" in tamper_report["reason"]
