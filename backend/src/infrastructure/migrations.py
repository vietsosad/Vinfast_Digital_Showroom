"""Small, idempotent schema upgrades for databases created before Phase 1 hardening.

``Base.metadata.create_all`` creates missing tables but never alters existing
ones. The steps below bring an older database to the current model; each step
checks first, so running them on every start-up is safe. Phase 2 should replace
this module with Alembic revisions.
"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

logger = logging.getLogger(__name__)


def _columns(connection: Connection, table: str) -> set[str]:
    return {column["name"] for column in inspect(connection).get_columns(table)}


def _indexes(connection: Connection, table: str) -> set[str]:
    return {index["name"] for index in inspect(connection).get_indexes(table)}


def add_booking_owner(connection: Connection) -> None:
    """0001: bookings are owned by an account id instead of a phone number."""
    if "user_id" in _columns(connection, "test_drive_bookings"):
        return
    logger.info("Migration 0001: adding test_drive_bookings.user_id")
    column_type = "UUID" if connection.dialect.name == "postgresql" else "CHAR(36)"
    connection.execute(text(f"ALTER TABLE test_drive_bookings ADD COLUMN user_id {column_type}"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS ix_test_drive_bookings_user_id ON test_drive_bookings (user_id)"))
    # Backfill only where the legacy phone identifies exactly one account; ambiguous
    # rows stay unowned (visible to staff only) rather than leaking to the wrong user.
    connection.execute(
        text(
            """
            UPDATE test_drive_bookings
            SET user_id = (SELECT a.user_id FROM accounts a WHERE a.phone = test_drive_bookings.customer_phone)
            WHERE user_id IS NULL
              AND (SELECT COUNT(*) FROM accounts a WHERE a.phone = test_drive_bookings.customer_phone) = 1
            """
        )
    )


def add_unique_phone(connection: Connection) -> None:
    """0002: one account per phone number."""
    if "ix_accounts_phone" in _indexes(connection, "accounts"):
        return
    duplicates = connection.execute(
        text("SELECT phone FROM accounts GROUP BY phone HAVING COUNT(*) > 1 LIMIT 1")
    ).first()
    if duplicates is not None:
        logger.warning("Migration 0002 skipped: duplicate phone numbers exist; resolve them, then restart")
        return
    logger.info("Migration 0002: adding unique index on accounts.phone")
    connection.execute(text("CREATE UNIQUE INDEX ix_accounts_phone ON accounts (phone)"))


MIGRATIONS = (add_booking_owner, add_unique_phone)


def run_migrations(connection: Connection) -> None:
    for migration in MIGRATIONS:
        migration(connection)
