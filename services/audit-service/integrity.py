"""
Integrity Verifier module.
Verifies log integrity using cryptographic hashing.
"""

import hashlib
import json
from typing import Optional

import structlog

from models import AuditLogEntry

logger = structlog.get_logger()


class IntegrityVerifier:
    """Verifies audit log integrity using hash chain."""

    def __init__(self, hash_algorithm: str = "sha256"):
        self.hash_algorithm = hash_algorithm

    def calculate_hash(self, entry: AuditLogEntry) -> str:
        """Calculate hash for an audit log entry."""
        # Create hash data excluding the hash field itself
        data = {
            "id": entry.id,
            "timestamp": entry.timestamp.isoformat(),
            "user_id": entry.user_id,
            "action": entry.action,
            "resource_type": entry.resource_type,
            "resource_id": entry.resource_id,
            "service": entry.service,
            "details": entry.details,
            "ip_address": entry.ip_address,
            "user_agent": entry.user_agent,
            "request_id": entry.request_id,
            "previous_hash": entry.previous_hash,
        }

        # Convert to canonical JSON string
        json_data = json.dumps(data, sort_keys=True, separators=(",", ":"))

        # Calculate hash
        if self.hash_algorithm == "sha256":
            hash_value = hashlib.sha256(json_data.encode()).hexdigest()
        elif self.hash_algorithm == "sha512":
            hash_value = hashlib.sha512(json_data.encode()).hexdigest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {self.hash_algorithm}")

        return hash_value

    def verify_hash(self, entry: AuditLogEntry) -> bool:
        """Verify the hash of an entry."""
        if not entry.hash:
            return False

        calculated = self.calculate_hash(entry)
        return calculated == entry.hash

    def verify_chain(
        self,
        entries: list[AuditLogEntry],
    ) -> tuple[bool, list[str]]:
        """Verify the integrity of a chain of entries."""
        tampered = []

        for i, entry in enumerate(entries):
            # Verify entry hash
            if not self.verify_hash(entry):
                tampered.append(entry.id)
                continue

            # Verify chain link (skip first entry)
            if i > 0:
                previous_entry = entries[i - 1]
                if entry.previous_hash != previous_entry.hash:
                    tampered.append(entry.id)

        return len(tampered) == 0, tampered

    def generate_merkle_root(self, entries: list[AuditLogEntry]) -> Optional[str]:
        """Generate Merkle root hash for a set of entries."""
        if not entries:
            return None

        # Get all hashes
        hashes = [entry.hash for entry in entries if entry.hash]

        if not hashes:
            return None

        # Build Merkle tree
        while len(hashes) > 1:
            new_level = []
            for i in range(0, len(hashes), 2):
                if i + 1 < len(hashes):
                    # Combine two hashes
                    combined = hashes[i] + hashes[i + 1]
                    new_hash = hashlib.sha256(combined.encode()).hexdigest()
                else:
                    # Odd one out
                    new_hash = hashes[i]
                new_level.append(new_hash)
            hashes = new_level

        return hashes[0]
