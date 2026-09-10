import asyncio
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import init_db, AsyncSessionLocal
from app.services.lifecycle import IdentityLifecycleService
from app.models.schemas import OnboardRequest, EmergencyKillSwitchRequest

SEED_EMPLOYEES = [
    {
        "full_name": "Elena Rostova",
        "email": "elena.rostova@enterprise.io",
        "department": "Platform Engineering",
        "role": "DEVOPS_ENGINEER",
        "github_username": "elena-infra",
        "slack_handle": "@elena.rostova"
    },
    {
        "full_name": "Marcus Chen",
        "email": "marcus.chen@enterprise.io",
        "department": "Core Backend",
        "role": "SOFTWARE_ENGINEER",
        "github_username": "marcus-chen",
        "slack_handle": "@marcus.chen"
    },
    {
        "full_name": "Sarah Jenkins",
        "email": "sarah.jenkins@enterprise.io",
        "department": "Product Management",
        "role": "PRODUCT_MANAGER",
        "github_username": "sarah-pm",
        "slack_handle": "@sarah.j"
    },
    {
        "full_name": "David Alverez",
        "email": "david.alverez@enterprise.io",
        "department": "Finance Operations",
        "role": "FINANCE_ANALYST",
        "github_username": None,
        "slack_handle": "@david.a"
    },
    {
        "full_name": "Lucas Vance",
        "email": "lucas.vance@enterprise.io",
        "department": "Security Architecture",
        "role": "DEVOPS_ENGINEER",
        "github_username": "lucas-sec",
        "slack_handle": "@lucas.vance"
    }
]

async def seed_directory():
    print("Initializing Database & Seeding Identity Directory & SOC2 Audit Chain...")
    await init_db()

    service = IdentityLifecycleService()
    async with AsyncSessionLocal() as db:
        created_ids = []
        for emp_data in SEED_EMPLOYEES:
            try:
                req = OnboardRequest(
                    full_name=emp_data["full_name"],
                    email=emp_data["email"],
                    department=emp_data["department"],
                    role=emp_data["role"],
                    github_username=emp_data["github_username"],
                    slack_handle=emp_data["slack_handle"],
                    initiator="HR Automated Pipeline"
                )
                emp = await service.onboard_employee(req, db)
                created_ids.append(emp.id)
                print(f"Provisioned identity: {emp.full_name} ({emp.role}) -> Status: {emp.status}")
            except Exception as e:
                print(f"Skipping {emp_data['email']}: {e}")

        # Simulate 1 historical Emergency Kill-Switch for Lucas Vance
        if created_ids:
            try:
                target_id = created_ids[-1]
                kill_req = EmergencyKillSwitchRequest(
                    reason="Compromised API Key Detected / Security Incident",
                    initiator="Chief Information Security Officer",
                    authorization_code="SEC-KILL-778"
                )
                await service.emergency_killswitch(target_id, kill_req, db)
                print(f"Executed Historical KillSwitch for employee ID: {target_id}")
            except Exception as e:
                print(f"KillSwitch simulation notice: {e}")

    print("Identity Directory & Cryptographic SOC2 Audit Chain seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_directory())
