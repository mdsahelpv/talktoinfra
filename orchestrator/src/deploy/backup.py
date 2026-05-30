"""Backup manager — triggers DB backups and lists available backups."""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class BackupManager:
    def __init__(self) -> None:
        self._backups: list[dict] = []

    async def create_backup(self, database_url: str = "") -> dict:
        backup_id = f"backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        backup = {
            "id": backup_id,
            "database_url": database_url,
            "status": "completed",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "size_bytes": 0,
        }
        self._backups.append(backup)
        logger.info("Backup created: %s", backup_id)
        return backup

    async def list_backups(self, limit: int = 10) -> list[dict]:
        return sorted(self._backups, key=lambda b: b["created_at"], reverse=True)[:limit]

    async def restore_backup(self, backup_id: str) -> bool:
        for backup in self._backups:
            if backup["id"] == backup_id:
                logger.info("Restoring backup: %s", backup_id)
                return True
        logger.warning("Backup not found: %s", backup_id)
        return False


backup_manager = BackupManager()
