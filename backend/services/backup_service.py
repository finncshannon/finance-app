"""Backup service for user_data.db.

Strategy (from phase0e Section 1.5 and phase0b):
- Daily automatic backup of user_data.db using SQLite .backup() API
- 30-day retention (auto-delete older backups)
- Filename format: user_data_YYYYMMDD_HHMMSS.db
- Only user_data.db is backed up (market_cache.db is regenerable)
"""

import asyncio
import logging
import os
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from db.connection import DatabaseConnection

logger = logging.getLogger("finance_app.backup")

DEFAULT_RETENTION_DAYS = 30
DEFAULT_SCHEDULE_HOUR = 2  # 2:00 AM


class BackupService:
    """Manages backups of user_data.db."""

    def __init__(
        self,
        db: DatabaseConnection,
        backup_dir: Path | None = None,
        retention_days: int = DEFAULT_RETENTION_DAYS,
        schedule_hour: int = DEFAULT_SCHEDULE_HOUR,
    ):
        self.db = db
        self.backup_dir = backup_dir or (db.data_dir / "backups")
        self.retention_days = retention_days
        self.schedule_hour = schedule_hour
        self._last_backup_date: str | None = None

    async def create_backup(self) -> dict:
        """Create a backup of user_data.db using SQLite .backup() API.

        Returns dict with backup metadata.
        """
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now(timezone.utc)
        filename = f"user_data_{now.strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = self.backup_dir / filename

        # Use synchronous sqlite3 .backup() API — safe even during writes
        src_path = str(self.db.user_db_path)
        dst_path = str(backup_path)

        def _do_backup():
            src = sqlite3.connect(src_path)
            dst = sqlite3.connect(dst_path)
            try:
                src.backup(dst)
            finally:
                dst.close()
                src.close()

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _do_backup)

        file_size = os.path.getsize(backup_path)
        self._last_backup_date = now.strftime("%Y-%m-%d")

        logger.info(f"Backup created: {filename} ({file_size} bytes)")

        # Clean up old backups
        self._cleanup_old_backups()

        return {
            "filename": filename,
            "file_path": str(backup_path),
            "file_size_bytes": file_size,
            "created_at": now.isoformat(),
        }

    def list_backups(self) -> list[dict]:
        """List all available backup files with metadata."""
        if not self.backup_dir.exists():
            return []

        backups = []
        for f in sorted(self.backup_dir.glob("user_data_*.db"), reverse=True):
            stat = f.stat()
            backups.append({
                "filename": f.name,
                "file_size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            })

        return backups

    async def restore_backup(self, filename: str) -> dict:
        """Restore user_data.db from a backup file.

        Closes current connection, copies backup over live db, reconnects.
        """
        backup_path = self.backup_dir / filename
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {filename}")

        # Close current db connection
        await self.db.close()

        # Copy backup over live database
        shutil.copy2(str(backup_path), str(self.db.user_db_path))

        # Reconnect
        await self.db.connect()

        logger.info(f"Database restored from backup: {filename}")

        return {
            "restored_from": filename,
            "restored_at": datetime.now(timezone.utc).isoformat(),
        }

    def _cleanup_old_backups(self) -> None:
        """Delete backups older than retention period."""
        if not self.backup_dir.exists():
            return

        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)

        for f in self.backup_dir.glob("user_data_*.db"):
            stat = f.stat()
            file_time = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            if file_time < cutoff:
                f.unlink()
                logger.info(f"Deleted old backup: {f.name}")

    async def run_scheduler(self) -> None:
        """Background task: run daily backup at configured hour.

        Runs on first launch of each day and at the scheduled hour.
        """
        while True:
            try:
                now = datetime.now(timezone.utc)
                today = now.strftime("%Y-%m-%d")

                # If we haven't backed up today, do it now (first launch of the day)
                if self._last_backup_date != today:
                    logger.info("Running daily backup...")
                    await self.create_backup()

                # Calculate seconds until next scheduled backup
                next_backup = now.replace(
                    hour=self.schedule_hour, minute=0, second=0, microsecond=0
                )
                if next_backup <= now:
                    next_backup += timedelta(days=1)

                sleep_seconds = (next_backup - now).total_seconds()
                await asyncio.sleep(sleep_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Backup scheduler error: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour on error
