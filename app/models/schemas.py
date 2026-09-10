from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from pydantic import BaseModel, EmailStr, Field
from app.core.database import Base

# --- SQLAlchemy Database Models ---

class EmployeeModel(Base):
    __tablename__ = "employees"

    id = Column(String(64), primary_key=True, index=True)
    full_name = Column(String(128), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    department = Column(String(64), nullable=False)
    role = Column(String(64), nullable=False) # e.g. SOFTWARE_ENGINEER, DEVOPS_ENGINEER
    
    # SaaS Handles
    github_username = Column(String(64), nullable=True)
    slack_handle = Column(String(64), nullable=True)
    aws_iam_user = Column(String(64), nullable=True)

    # Lifecycle Status: ACTIVE, OFFBOARDED, KILLSWITCH_TERMINATED
    status = Column(String(32), default="ACTIVE", index=True)
    
    # Timestamps & Audit
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    offboarded_at = Column(DateTime, nullable=True)
    provisioned_by = Column(String(128), default="System")
    offboarded_by = Column(String(128), nullable=True)

    # Relationships
    access_grants = relationship("AccessGrantModel", back_populates="employee", cascade="all, delete-orphan", lazy="selectin")


class AccessGrantModel(Base):
    __tablename__ = "access_grants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String(64), ForeignKey("employees.id"), nullable=False)
    platform = Column(String(32), nullable=False) # "GITHUB", "SLACK", "AWS_IAM"
    resource_name = Column(String(255), nullable=False) # e.g. "team:backend-devs" or "role:DeveloperSandboxAccess"
    access_level = Column(String(32), nullable=False) # "push", "admin", "channel_member"
    is_active = Column(Boolean, default=True)
    granted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    revoked_at = Column(DateTime, nullable=True)

    employee = relationship("EmployeeModel", back_populates="access_grants")


# --- Pydantic Request / Response Schemas ---

class OnboardRequest(BaseModel):
    full_name: str = Field(..., json_schema_extra={"example": "Alice Vance"})
    email: EmailStr = Field(..., json_schema_extra={"example": "alice.vance@enterprise.io"})
    department: str = Field(..., json_schema_extra={"example": "Engineering"})
    role: str = Field(..., json_schema_extra={"example": "SOFTWARE_ENGINEER"})
    github_username: Optional[str] = Field(None, json_schema_extra={"example": "alice-vance"})
    slack_handle: Optional[str] = Field(None, json_schema_extra={"example": "@alice.vance"})
    initiator: str = "HR Operations"

class OffboardRequest(BaseModel):
    reason: str = Field(..., json_schema_extra={"example": "Voluntary Resignation"})
    initiator: str = "SecOps Lead"
    notes: Optional[str] = None

class EmergencyKillSwitchRequest(BaseModel):
    reason: str = Field(..., json_schema_extra={"example": "Security Compromise / Hostile Departure"})
    initiator: str = "CISO / Lead SecOps"
    authorization_code: str = Field(..., json_schema_extra={"example": "SEC-KILL-991"})

class AccessGrantSchema(BaseModel):
    id: int
    platform: str
    resource_name: str
    access_level: str
    is_active: bool
    granted_at: datetime
    revoked_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class EmployeeResponse(BaseModel):
    id: str
    full_name: str
    email: str
    department: str
    role: str
    github_username: Optional[str] = None
    slack_handle: Optional[str] = None
    aws_iam_user: Optional[str] = None
    status: str
    created_at: datetime
    offboarded_at: Optional[datetime] = None
    provisioned_by: Optional[str] = None
    offboarded_by: Optional[str] = None
    access_grants: List[AccessGrantSchema] = []

    model_config = {"from_attributes": True}

class AuditBlockResponse(BaseModel):
    index: int
    timestamp: datetime
    action: str
    target_user_id: str
    target_email: str
    actor: str
    details: str
    previous_hash: str
    block_hash: str

    model_config = {"from_attributes": True}
