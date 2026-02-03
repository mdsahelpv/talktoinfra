"""
Log Store module.
Manages storage and retrieval of audit logs.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

from models import AuditLogEntry

logger = structlog.get_logger()


class LogStore:
    """Stores and retrieves audit logs."""

    def __init__(self, storage_path: str, retention_days: int):
        self.storage_path = storage_path
        self.retention_days = retention_days
        self.logs: List[AuditLogEntry] = []  # In-memory store for demo
        self.last_hash: Optional[str] = None

        # Ensure storage directory exists
        os.makedirs(storage_path, exist_ok=True)

    async def store(self, entry: AuditLogEntry):
        """Store an audit log entry."""
        self.logs.append(entry)
        self.last_hash = entry.hash

        # In production, write to persistent storage
        # await self._write_to_disk(entry)

        logger.debug("log_entry_stored", entry_id=entry.id)

    async def _write_to_disk(self, entry: AuditLogEntry):
        """Write entry to disk (production implementation)."""
        # Organize by date
        date_str = entry.timestamp.strftime("%Y-%m-%d")
        file_path = os.path.join(self.storage_path, f"audit-{date_str}.log")

        with open(file_path, "a") as f:
            f.write(json.dumps(entry.model_dump(), default=str) + "\n")

    async def query(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLogEntry]:
        """Query audit logs."""
        results = self.logs.copy()

        # Filter by time range
        if start_time:
            results = [log for log in results if log.timestamp >= start_time]
        if end_time:
            results = [log for log in results if log.timestamp <= end_time]

        # Apply filters
        if filters:
            for key, value in filters.items():
                if value is not None:
                    results = [
                        log for log in results if getattr(log, key, None) == value
                    ]

        # Sort by timestamp descending
        results.sort(key=lambda x: x.timestamp, reverse=True)

        # Apply limit and offset
        return results[offset : offset + limit]

    async def count(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Count matching audit logs."""
        results = await self.query(
            start_time=start_time,
            end_time=end_time,
            filters=filters,
            limit=1000000,
        )
        return len(results)

    async def get_by_id(self, entry_id: str) -> Optional[AuditLogEntry]:
        """Get a specific log entry by ID."""
        for log in self.logs:
            if log.id == entry_id:
                return log
        return None

    async def get_last_hash(self) -> Optional[str]:
        """Get the hash of the last entry."""
        return self.last_hash

    async def cleanup_old_logs(self):
        """Remove logs older than retention period."""
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
        old_count = len([log for log in self.logs if log.timestamp < cutoff])
        self.logs = [log for log in self.logs if log.timestamp >= cutoff]
        logger.info("old_logs_cleaned", removed=old_count, retained=len(self.logs))
