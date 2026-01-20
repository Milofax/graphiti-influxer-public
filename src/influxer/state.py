"""SQLite State Management Module for Graphiti Influxer.

Tracks ingestion state for files to support resume capability.

Edge cases handled:
- #44: Kill während DB-Write (SQLite transactions)
- #47: Disk voll (pre-check + clear error)
- #48: Parallele Instanzen (file locking via SQLite)
- #50: Network-Drive (documented: local recommended)
- #75: File-Handles (context managers)
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from influxer.config import get_state_db_path

logger = logging.getLogger(__name__)

# Minimum disk space required (10 MB)
MIN_DISK_SPACE_MB = 10

# Status values
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


def get_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file.

    Args:
        file_path: Path to the file

    Returns:
        Hex-encoded SHA256 hash
    """
    sha256 = hashlib.sha256()

    with file_path.open("rb") as f:
        # Read in chunks for large files
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def check_disk_space(path: Path, min_mb: int = MIN_DISK_SPACE_MB) -> bool:
    """Check if there's enough disk space (#47).

    Args:
        path: Path to check (uses parent directory for files)
        min_mb: Minimum required space in megabytes

    Returns:
        True if sufficient space available
    """
    try:
        # Get disk usage for the parent directory (where the file will be created)
        check_path = path.parent

        # Ensure parent directory exists (but don't create the file path as a directory!)
        check_path.mkdir(parents=True, exist_ok=True)

        usage = shutil.disk_usage(check_path)
        free_mb = usage.free / (1024 * 1024)

        if free_mb < min_mb:
            logger.warning(f"Low disk space: {free_mb:.1f}MB free (need {min_mb}MB)")
            return False

        return True

    except Exception as e:
        logger.warning(f"Could not check disk space: {e}")
        return True  # Assume OK if we can't check


class StateDB:
    """SQLite database for tracking ingestion state.

    Handles all edge cases related to SQLite:
    - #44: Atomic transactions
    - #48: Concurrent access with timeout
    - #75: Proper file handle management
    """

    def __init__(self, db_path: Path | None = None) -> None:
        """Initialize the state database.

        Args:
            db_path: Path to SQLite database file (default from config)
        """
        self.db_path = db_path or get_state_db_path()
        self._conn: sqlite3.Connection | None = None
        self._initialized = False

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection (#48, #75)."""
        if self._conn is None:
            # Ensure directory exists and has space (#47)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            if not check_disk_space(self.db_path):
                raise OSError(
                    f"Insufficient disk space for state database at {self.db_path}. "
                    f"Need at least {MIN_DISK_SPACE_MB}MB free."
                )

            # Connect with timeout for concurrent access (#48)
            self._conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,  # Wait up to 30s if locked
                isolation_level=None,  # Autocommit mode, we manage transactions manually
            )
            self._conn.row_factory = sqlite3.Row

            # Enable foreign keys and WAL mode for better concurrency
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA journal_mode = WAL")

        return self._conn

    def init_db(self) -> None:
        """Initialize database schema if not exists."""
        if self._initialized:
            return

        conn = self._get_connection()

        # Use transaction for schema creation (#44)
        conn.execute("BEGIN")
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ingestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_hash TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size INTEGER,
                    group_id TEXT NOT NULL,
                    chunk_count INTEGER DEFAULT 0,
                    chunks_sent INTEGER DEFAULT 0,
                    episode_uuids TEXT DEFAULT '[]',
                    status TEXT DEFAULT 'pending',
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    UNIQUE(file_hash, group_id)
                )
            """)

            # Index for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ingestions_file_hash
                ON ingestions(file_hash)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ingestions_status
                ON ingestions(status)
            """)

            conn.execute("COMMIT")
            self._initialized = True
            logger.debug(f"State database initialized at {self.db_path}")

        except Exception as e:
            conn.execute("ROLLBACK")
            raise RuntimeError(f"Failed to initialize database: {e}") from e

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Cursor]:
        """Context manager for database transactions (#44).

        Ensures atomic operations - either all succeed or all rollback.

        Yields:
            Database cursor for executing queries
        """
        conn = self._get_connection()
        self.init_db()

        conn.execute("BEGIN")
        cursor = conn.cursor()
        try:
            yield cursor
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def is_file_ingested(self, file_hash: str, group_id: str | None = None) -> bool:
        """Check if a file has already been ingested.

        Args:
            file_hash: SHA256 hash of the file
            group_id: Optional group ID to check specific ingestion

        Returns:
            True if file was successfully ingested
        """
        conn = self._get_connection()
        self.init_db()

        if group_id:
            result = conn.execute(
                "SELECT status FROM ingestions WHERE file_hash = ? AND group_id = ? AND status = ?",
                (file_hash, group_id, STATUS_COMPLETED),
            ).fetchone()
        else:
            result = conn.execute(
                "SELECT status FROM ingestions WHERE file_hash = ? AND status = ?",
                (file_hash, STATUS_COMPLETED),
            ).fetchone()

        return result is not None

    def get_ingestion_status(
        self, file_hash: str, group_id: str | None = None
    ) -> dict[str, Any] | None:
        """Get ingestion status for a file.

        Args:
            file_hash: SHA256 hash of the file
            group_id: Optional group ID to check specific ingestion

        Returns:
            Status dict or None if not found
        """
        conn = self._get_connection()
        self.init_db()

        if group_id:
            row = conn.execute(
                "SELECT * FROM ingestions WHERE file_hash = ? AND group_id = ?",
                (file_hash, group_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM ingestions WHERE file_hash = ? ORDER BY created_at DESC LIMIT 1",
                (file_hash,),
            ).fetchone()

        if row is None:
            return None

        return {
            "id": row["id"],
            "file_hash": row["file_hash"],
            "file_path": row["file_path"],
            "file_name": row["file_name"],
            "file_size": row["file_size"],
            "group_id": row["group_id"],
            "chunk_count": row["chunk_count"],
            "chunks_sent": row["chunks_sent"],
            "episode_uuids": json.loads(row["episode_uuids"]),
            "status": row["status"],
            "error_message": row["error_message"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "completed_at": row["completed_at"],
        }

    def start_ingestion(
        self,
        file_hash: str,
        file_path: Path,
        group_id: str,
        chunk_count: int,
    ) -> int:
        """Record the start of an ingestion.

        Args:
            file_hash: SHA256 hash of the file
            file_path: Path to the file
            group_id: Graphiti group ID
            chunk_count: Total number of chunks to send

        Returns:
            Ingestion record ID
        """
        now = datetime.utcnow().isoformat()

        with self.transaction() as cursor:
            # Check for existing ingestion
            existing = cursor.execute(
                "SELECT id, status FROM ingestions WHERE file_hash = ? AND group_id = ?",
                (file_hash, group_id),
            ).fetchone()

            if existing:
                # Update existing record
                cursor.execute(
                    """
                    UPDATE ingestions SET
                        file_path = ?,
                        chunk_count = ?,
                        chunks_sent = 0,
                        episode_uuids = '[]',
                        status = ?,
                        error_message = NULL,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (str(file_path), chunk_count, STATUS_IN_PROGRESS, now, existing["id"]),
                )
                return int(existing["id"])
            else:
                # Create new record
                cursor.execute(
                    """
                    INSERT INTO ingestions (
                        file_hash, file_path, file_name, file_size, group_id,
                        chunk_count, chunks_sent, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                    """,
                    (
                        file_hash,
                        str(file_path),
                        file_path.name,
                        file_path.stat().st_size,
                        group_id,
                        chunk_count,
                        STATUS_IN_PROGRESS,
                        now,
                        now,
                    ),
                )
                return cursor.lastrowid or 0

    def update_progress(
        self,
        ingestion_id: int,
        chunks_sent: int,
        episode_uuid: str | None = None,
    ) -> None:
        """Update ingestion progress.

        Args:
            ingestion_id: Ingestion record ID
            chunks_sent: Number of chunks successfully sent
            episode_uuid: UUID of the episode just created (optional)
        """
        now = datetime.utcnow().isoformat()

        with self.transaction() as cursor:
            if episode_uuid:
                # Get current episode UUIDs and append
                row = cursor.execute(
                    "SELECT episode_uuids FROM ingestions WHERE id = ?",
                    (ingestion_id,),
                ).fetchone()

                if row:
                    uuids = json.loads(row["episode_uuids"])
                    uuids.append(episode_uuid)
                    cursor.execute(
                        """
                        UPDATE ingestions SET
                            chunks_sent = ?,
                            episode_uuids = ?,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (chunks_sent, json.dumps(uuids), now, ingestion_id),
                    )
            else:
                cursor.execute(
                    "UPDATE ingestions SET chunks_sent = ?, updated_at = ? WHERE id = ?",
                    (chunks_sent, now, ingestion_id),
                )

    def complete_ingestion(self, ingestion_id: int) -> None:
        """Mark ingestion as completed.

        Args:
            ingestion_id: Ingestion record ID
        """
        now = datetime.utcnow().isoformat()

        with self.transaction() as cursor:
            cursor.execute(
                """
                UPDATE ingestions SET
                    status = ?,
                    updated_at = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (STATUS_COMPLETED, now, now, ingestion_id),
            )

    def fail_ingestion(self, ingestion_id: int, error_message: str) -> None:
        """Mark ingestion as failed.

        Args:
            ingestion_id: Ingestion record ID
            error_message: Error description
        """
        now = datetime.utcnow().isoformat()

        with self.transaction() as cursor:
            cursor.execute(
                """
                UPDATE ingestions SET
                    status = ?,
                    error_message = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (STATUS_FAILED, error_message, now, ingestion_id),
            )

    def record_ingestion(
        self,
        file_hash: str,
        file_path: str,
        group_id: str,
        chunk_count: int,
        episode_uuids: list[str],
    ) -> None:
        """Record a completed ingestion (convenience method).

        Args:
            file_hash: SHA256 hash of the file
            file_path: Path to the file
            group_id: Graphiti group ID
            chunk_count: Total number of chunks sent
            episode_uuids: List of episode UUIDs created
        """
        path = Path(file_path)
        ingestion_id = self.start_ingestion(file_hash, path, group_id, chunk_count)

        with self.transaction() as cursor:
            now = datetime.utcnow().isoformat()
            cursor.execute(
                """
                UPDATE ingestions SET
                    chunks_sent = ?,
                    episode_uuids = ?,
                    status = ?,
                    updated_at = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    chunk_count,
                    json.dumps(episode_uuids),
                    STATUS_COMPLETED,
                    now,
                    now,
                    ingestion_id,
                ),
            )

    def get_pending_ingestions(self) -> list[dict[str, Any]]:
        """Get all pending or in-progress ingestions for resume.

        Returns:
            List of ingestion status dicts
        """
        conn = self._get_connection()
        self.init_db()

        rows = conn.execute(
            "SELECT * FROM ingestions WHERE status IN (?, ?) ORDER BY created_at",
            (STATUS_PENDING, STATUS_IN_PROGRESS),
        ).fetchall()

        return [
            {
                "id": row["id"],
                "file_hash": row["file_hash"],
                "file_path": row["file_path"],
                "file_name": row["file_name"],
                "group_id": row["group_id"],
                "chunk_count": row["chunk_count"],
                "chunks_sent": row["chunks_sent"],
                "status": row["status"],
            }
            for row in rows
        ]

    def close(self) -> None:
        """Close database connection (#75)."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> StateDB:
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: Any,
    ) -> None:
        """Context manager exit (#75)."""
        self.close()
