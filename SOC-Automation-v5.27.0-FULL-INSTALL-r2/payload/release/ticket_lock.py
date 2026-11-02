from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path


class TicketLockStore:
    """SQLite lease store untuk mencegah pemrosesan tiket lintas-process."""

    def __init__(self, database: str | Path, owner_id: str, *, lease_seconds: int = 21600) -> None:
        self.database = Path(database).expanduser().resolve()
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.owner_id = owner_id
        self.lease_seconds = lease_seconds
        self._local = threading.local()
        self._initialize()

    def _connection(self) -> sqlite3.Connection:
        connection = getattr(self._local, "connection", None)
        if connection is None:
            connection = sqlite3.connect(self.database, timeout=10, isolation_level=None)
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA busy_timeout=10000")
            connection.execute("PRAGMA synchronous=NORMAL")
            self._local.connection = connection
        return connection

    def _initialize(self) -> None:
        connection = sqlite3.connect(self.database, timeout=10)
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ticket_leases (
                    ticket_key TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    acquired_at REAL NOT NULL,
                    renewed_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_ticket_leases_expiry ON ticket_leases(expires_at)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ticket_processing_state (
                    ticket_key TEXT PRIMARY KEY,
                    state TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    failure_code TEXT,
                    next_retry_at REAL,
                    cooldown_until REAL,
                    payload_fingerprint TEXT,
                    result_fingerprint TEXT,
                    notification_fingerprint TEXT,
                    notification_sent_at REAL,
                    completed_at REAL,
                    updated_at REAL NOT NULL,
                    CHECK (
                        state IN (
                            'pending',
                            'processing',
                            'retry_wait',
                            'completed',
                            'blocked_manual_review'
                        )
                    ),
                    CHECK (attempts >= 0)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ticket_processing_retry
                ON ticket_processing_state(state, next_retry_at)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ticket_processing_cooldown
                ON ticket_processing_state(state, cooldown_until)
                """
            )
            connection.commit()
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ticket_manual_disposition (
                    ticket_key TEXT PRIMARY KEY,
                    disposition TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    dismissed_at REAL NOT NULL,
                    raw_cleanup_after REAL,
                    restored_at REAL,
                    CHECK (disposition IN ('dismissed_manual'))
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_manual_disposition_cleanup ON ticket_manual_disposition(raw_cleanup_after)"
            )
            connection.commit()
        finally:
            connection.close()

    def acquire(self, ticket_key: str) -> bool:
        now = time.time()
        expires = now + self.lease_seconds
        connection = self._connection()
        connection.execute("BEGIN IMMEDIATE")
        try:
            row = connection.execute(
                "SELECT owner_id, expires_at FROM ticket_leases WHERE ticket_key = ?",
                (ticket_key,),
            ).fetchone()
            if row is not None and row[0] != self.owner_id and float(row[1]) > now:
                connection.execute("ROLLBACK")
                return False
            connection.execute(
                """
                INSERT INTO ticket_leases(ticket_key, owner_id, acquired_at, renewed_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(ticket_key) DO UPDATE SET
                    owner_id=excluded.owner_id,
                    acquired_at=excluded.acquired_at,
                    renewed_at=excluded.renewed_at,
                    expires_at=excluded.expires_at
                """,
                (ticket_key, self.owner_id, now, now, expires),
            )
            connection.execute("COMMIT")
            return True
        except Exception:
            connection.execute("ROLLBACK")
            raise

    def renew_owned(self) -> int:
        now = time.time()
        cursor = self._connection().execute(
            "UPDATE ticket_leases SET renewed_at = ?, expires_at = ? WHERE owner_id = ?",
            (now, now + self.lease_seconds, self.owner_id),
        )
        return cursor.rowcount

    def release(self, ticket_key: str) -> None:
        self._connection().execute(
            "DELETE FROM ticket_leases WHERE ticket_key = ? AND owner_id = ?",
            (ticket_key, self.owner_id),
        )

    def release_all(self) -> int:
        cursor = self._connection().execute(
            "DELETE FROM ticket_leases WHERE owner_id = ?",
            (self.owner_id,),
        )
        return cursor.rowcount

    def cleanup_expired(self) -> int:
        cursor = self._connection().execute(
            "DELETE FROM ticket_leases WHERE expires_at <= ?",
            (time.time(),),
        )
        return cursor.rowcount

    def claim_failure_notification(
        self,
        ticket_key,
        failure_code,
        cooldown_seconds=1800.0,
        now=None,
    ):
        current_time = (
            time.time()
            if now is None
            else float(now)
        )

        normalized_code = str(
            failure_code or "PROCESSING_FAILED"
        ).strip().upper()[:128]

        connection = self._connection()
        connection.execute("BEGIN IMMEDIATE")

        try:
            row = connection.execute(
                """
                SELECT
                    notification_fingerprint,
                    notification_sent_at
                FROM ticket_processing_state
                WHERE ticket_key = ?
                """,
                (ticket_key,),
            ).fetchone()

            if row is not None:
                previous_code = row[0]
                previous_sent_at = row[1]

                if (
                    previous_code == normalized_code
                    and previous_sent_at is not None
                    and (
                        float(previous_sent_at)
                        + float(cooldown_seconds)
                        > current_time
                    )
                ):
                    connection.execute("ROLLBACK")
                    return False

            connection.execute(
                """
                INSERT INTO ticket_processing_state (
                    ticket_key,
                    state,
                    attempts,
                    notification_fingerprint,
                    notification_sent_at,
                    updated_at
                )
                VALUES (?, 'pending', 0, ?, ?, ?)
                ON CONFLICT(ticket_key) DO UPDATE SET
                    notification_fingerprint=excluded.notification_fingerprint,
                    notification_sent_at=excluded.notification_sent_at,
                    updated_at=excluded.updated_at
                """,
                (
                    ticket_key,
                    normalized_code,
                    current_time,
                    current_time,
                ),
            )

            connection.execute("COMMIT")
            return True

        except Exception:
            connection.execute("ROLLBACK")
            raise


    def mark_completed(
        self,
        ticket_key,
        payload_fingerprint=None,
        result_fingerprint=None,
    ):
        now = time.time()

        current = self.processing_state(ticket_key)

        if current is None:
            attempts = 1
        else:
            attempts = int(
                current.get("attempts") or 1
            )

        self._connection().execute(
            """
            INSERT INTO ticket_processing_state (
                ticket_key,
                state,
                attempts,
                failure_code,
                next_retry_at,
                cooldown_until,
                payload_fingerprint,
                result_fingerprint,
                completed_at,
                updated_at
            )
            VALUES (
                ?,
                'completed',
                ?,
                NULL,
                NULL,
                NULL,
                ?,
                ?,
                ?,
                ?
            )
            ON CONFLICT(ticket_key) DO UPDATE SET
                state='completed',
                attempts=excluded.attempts,
                failure_code=NULL,
                next_retry_at=NULL,
                cooldown_until=NULL,
                payload_fingerprint=excluded.payload_fingerprint,
                result_fingerprint=excluded.result_fingerprint,
                completed_at=excluded.completed_at,
                updated_at=excluded.updated_at
            """,
            (
                ticket_key,
                attempts,
                payload_fingerprint,
                result_fingerprint,
                now,
                now,
            ),
        )

        return self.processing_state(ticket_key)


    def mark_failure(
        self,
        ticket_key,
        failure_code,
        retry_delays=(60.0, 180.0, 600.0),
        max_attempts=3,
    ):
        now = time.time()

        current = self.processing_state(ticket_key)

        if current is None:
            attempts = 1
        else:
            attempts = int(current.get("attempts") or 0)

            if attempts == 0:
                attempts = 1

        normalized_code = str(
            failure_code or "PROCESSING_FAILED"
        ).strip()[:128]

        blocked = attempts not in range(max_attempts)

        if blocked:
            state = "blocked_manual_review"
            next_retry_at = None
            cooldown_until = now + 1800.0
        else:
            state = "retry_wait"

            delay_index = max(
                0,
                min(
                    attempts - 1,
                    len(retry_delays) - 1,
                ),
            )

            next_retry_at = (
                now
                + float(retry_delays[delay_index])
            )

            cooldown_until = next_retry_at

        self._connection().execute(
            """
            INSERT INTO ticket_processing_state (
                ticket_key,
                state,
                attempts,
                failure_code,
                next_retry_at,
                cooldown_until,
                completed_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, NULL, ?)
            ON CONFLICT(ticket_key) DO UPDATE SET
                state=excluded.state,
                attempts=excluded.attempts,
                failure_code=excluded.failure_code,
                next_retry_at=excluded.next_retry_at,
                cooldown_until=excluded.cooldown_until,
                completed_at=NULL,
                updated_at=excluded.updated_at
            """,
            (
                ticket_key,
                state,
                attempts,
                normalized_code,
                next_retry_at,
                cooldown_until,
                now,
            ),
        )

        return self.processing_state(ticket_key)

    def mark_processing(self, ticket_key: str):
        now = time.time()
        self._connection().execute(
            """
            INSERT INTO ticket_processing_state (
                ticket_key,
                state,
                attempts,
                failure_code,
                next_retry_at,
                cooldown_until,
                completed_at,
                updated_at
            )
            VALUES (?, 'processing', 1, NULL, NULL, NULL, NULL, ?)
            ON CONFLICT(ticket_key) DO UPDATE SET
                state='processing',
                attempts=ticket_processing_state.attempts + 1,
                failure_code=NULL,
                next_retry_at=NULL,
                cooldown_until=NULL,
                completed_at=NULL,
                updated_at=excluded.updated_at
            """,
            (
                ticket_key,
                now,
            ),
        )
        return self.processing_state(ticket_key)
    def requeue_validated(self, ticket_key: str):
        """Requeue a failed ticket only when no live lease exists."""
        now = time.time()
        connection = self._connection()
        connection.execute("BEGIN IMMEDIATE")
        try:
            lease = connection.execute(
                "SELECT owner_id, expires_at FROM ticket_leases WHERE ticket_key = ?",
                (ticket_key,),
            ).fetchone()
            if lease is not None and float(lease[1]) > now:
                raise RuntimeError("TICKET_HAS_ACTIVE_LEASE")
            row = connection.execute(
                "SELECT state FROM ticket_processing_state WHERE ticket_key = ?",
                (ticket_key,),
            ).fetchone()
            if row is None:
                raise RuntimeError("TICKET_STATE_NOT_FOUND")
            if row[0] not in {"blocked_manual_review", "retry_wait"}:
                raise RuntimeError("TICKET_STATE_NOT_REQUEUEABLE")
            connection.execute(
                """
                UPDATE ticket_processing_state
                SET state='pending',
                    attempts=0,
                    failure_code=NULL,
                    next_retry_at=NULL,
                    cooldown_until=NULL,
                    payload_fingerprint=NULL,
                    result_fingerprint=NULL,
                    completed_at=NULL,
                    updated_at=?
                WHERE ticket_key=?
                """,
                (now, ticket_key),
            )
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        return self.processing_state(ticket_key)

    def processing_state(
        self,
        ticket_key: str,
    ) -> dict[str, object] | None:
        row = self._connection().execute(
            """
            SELECT
                ticket_key,
                state,
                attempts,
                failure_code,
                next_retry_at,
                cooldown_until,
                payload_fingerprint,
                result_fingerprint,
                notification_fingerprint,
                notification_sent_at,
                completed_at,
                updated_at
            FROM ticket_processing_state
            WHERE ticket_key = ?
            """,
            (ticket_key,),
        ).fetchone()

        if row is None:
            return None

        return {
            "ticket_key": row[0],
            "state": row[1],
            "attempts": int(row[2]),
            "failure_code": row[3],
            "next_retry_at": row[4],
            "cooldown_until": row[5],
            "payload_fingerprint": row[6],
            "result_fingerprint": row[7],
            "notification_fingerprint": row[8],
            "notification_sent_at": row[9],
            "completed_at": row[10],
            "updated_at": row[11],
        }

    def manual_disposition(self, ticket_key: str):
        row = self._connection().execute(
            "SELECT disposition, reason, actor, dismissed_at, raw_cleanup_after, restored_at "
            "FROM ticket_manual_disposition WHERE ticket_key = ?",
            (ticket_key,),
        ).fetchone()
        if row is None:
            return None
        return {
            "disposition": row[0],
            "reason": row[1],
            "actor": row[2],
            "dismissed_at": row[3],
            "raw_cleanup_after": row[4],
            "restored_at": row[5],
        }

    def dismiss_reprocessing(
        self, ticket_key: str, *, reason: str, actor: str,
        cleanup_after: float | None = None, now: float | None = None,
    ):
        current_time = time.time() if now is None else float(now)
        reason = str(reason).strip()
        actor = str(actor).strip()
        if not reason:
            raise ValueError("dismissal reason is required")
        if not actor:
            raise ValueError("dismissal actor is required")
        connection = self._connection()
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute(
                "DELETE FROM ticket_leases WHERE ticket_key = ?", (ticket_key,)
            )
            connection.execute(
                """
                INSERT INTO ticket_manual_disposition(
                    ticket_key, disposition, reason, actor, dismissed_at,
                    raw_cleanup_after, restored_at
                ) VALUES (?, 'dismissed_manual', ?, ?, ?, ?, NULL)
                ON CONFLICT(ticket_key) DO UPDATE SET
                    disposition='dismissed_manual', reason=excluded.reason,
                    actor=excluded.actor, dismissed_at=excluded.dismissed_at,
                    raw_cleanup_after=excluded.raw_cleanup_after, restored_at=NULL
                """,
                (ticket_key, reason, actor, current_time, cleanup_after),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        return self.manual_disposition(ticket_key)

    def restore_reprocessing(self, ticket_key: str, now: float | None = None):
        current_time = time.time() if now is None else float(now)
        connection = self._connection()
        connection.execute("BEGIN IMMEDIATE")
        try:
            changed = connection.execute(
                "DELETE FROM ticket_manual_disposition WHERE ticket_key = ?",
                (ticket_key,),
            ).rowcount
            if changed:
                connection.execute(
                    """
                    INSERT INTO ticket_processing_state(
                        ticket_key, state, attempts, failure_code, next_retry_at,
                        cooldown_until, updated_at
                    ) VALUES (?, 'pending', 0, NULL, NULL, NULL, ?)
                    ON CONFLICT(ticket_key) DO UPDATE SET
                        state='pending', failure_code=NULL, next_retry_at=NULL,
                        cooldown_until=NULL, updated_at=excluded.updated_at
                    """,
                    (ticket_key, current_time),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        return bool(changed)

    def processing_allowed(
        self,
        ticket_key: str,
        now=None,
    ):
        if now is None:
            current_time = time.time()
        else:
            current_time = float(now)

        disposition = self.manual_disposition(ticket_key)
        if disposition is not None:
            return False, "dismissed_manual"

        state = self.processing_state(ticket_key)

        if state is None:
            return True, "new"

        status = str(state.get("state") or "pending")

        if status == "completed":
            return False, "completed"

        if status == "blocked_manual_review":
            return False, "blocked_manual_review"

        cooldown_until = state.get("cooldown_until")

        if cooldown_until is not None:
            if float(cooldown_until) > current_time:
                return False, "cooldown"

        next_retry_at = state.get("next_retry_at")

        if status == "retry_wait":
            if next_retry_at is not None:
                if float(next_retry_at) > current_time:
                    return False, "retry_wait"

        return True, status

    def inspect(self) -> list[dict[str, object]]:
        rows = self._connection().execute(
            "SELECT ticket_key, owner_id, acquired_at, renewed_at, expires_at FROM ticket_leases ORDER BY ticket_key"
        ).fetchall()
        return [
            {
                "ticket_key": row[0],
                "owner_id": row[1],
                "acquired_at": row[2],
                "renewed_at": row[3],
                "expires_at": row[4],
            }
            for row in rows
        ]

    def close(self) -> None:
        connection = getattr(self._local, "connection", None)
        if connection is not None:
            connection.close()
            self._local.connection = None
