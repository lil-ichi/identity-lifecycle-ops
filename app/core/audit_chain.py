import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.core.database import Base

class AuditBlockModel(Base):
    __tablename__ = "audit_chain"

    index = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    action = Column(String(64), nullable=False) # e.g. "ONBOARD_PROVISION", "EMERGENCY_KILLSWITCH", "TOKEN_REVOKE"
    target_user_id = Column(String(128), nullable=False)
    target_email = Column(String(255), nullable=False)
    actor = Column(String(128), nullable=False) # e.g. "SecOps Lead", "Automated HR Trigger"
    details = Column(Text, nullable=False) # JSON payload string
    previous_hash = Column(String(64), nullable=False)
    block_hash = Column(String(64), nullable=False, unique=True)

class AuditChainService:
    """
    Implements a tamper-evident, cryptographically chained audit log
    for SOC2 / ISO27001 identity compliance.
    """

    GENESIS_PREV_HASH = "0" * 64

    @classmethod
    def format_timestamp(cls, dt: datetime) -> str:
        """Converts datetime to standardized UTC ISO string."""
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    @classmethod
    def calculate_hash(
        cls,
        index: int,
        timestamp_str: str,
        action: str,
        target_user_id: str,
        target_email: str,
        actor: str,
        details_str: str,
        previous_hash: str
    ) -> str:
        """Computes SHA-256 hash across block parameters."""
        raw_data = f"{index}|{timestamp_str}|{action}|{target_user_id}|{target_email}|{actor}|{details_str}|{previous_hash}"
        return hashlib.sha256(raw_data.encode("utf-8")).hexdigest()

    @classmethod
    def verify_integrity(cls, blocks: List[AuditBlockModel]) -> Dict[str, Any]:
        """
        Walks the entire chain from Genesis block and cryptographically verifies
        all sequential hashes and previous_hash links.
        """
        if not blocks:
            return {"valid": True, "total_blocks": 0, "message": "Ledger is empty (Valid)"}

        for i, block in enumerate(blocks):
            # Check previous hash pointer
            expected_prev = cls.GENESIS_PREV_HASH if i == 0 else blocks[i - 1].block_hash
            if block.previous_hash != expected_prev:
                return {
                    "valid": False,
                    "tampered_index": block.index,
                    "reason": f"Broken chain link at block #{block.index}. Expected prev_hash {expected_prev}, got {block.previous_hash}."
                }

            # Recompute block hash
            time_str = cls.format_timestamp(block.timestamp)
            recomputed = cls.calculate_hash(
                block.index,
                time_str,
                block.action,
                block.target_user_id,
                block.target_email,
                block.actor,
                block.details,
                block.previous_hash
            )

            if block.block_hash != recomputed:
                return {
                    "valid": False,
                    "tampered_index": block.index,
                    "reason": f"Hash mismatch at block #{block.index}. Expected {recomputed}, recorded {block.block_hash}."
                }

        return {
            "valid": True,
            "total_blocks": len(blocks),
            "latest_block_hash": blocks[-1].block_hash,
            "message": f"Cryptographic integrity verified across {len(blocks)} audit blocks."
        }
