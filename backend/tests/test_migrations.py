"""Upgrading a database created before booking ownership existed."""

import shutil
import sqlite3
import tempfile
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

from src.infrastructure.migrations import run_migrations


@pytest.fixture
def workdir():
    path = Path(tempfile.mkdtemp(prefix="p101-migration-"))
    yield path
    shutil.rmtree(path, ignore_errors=True)


def legacy_database(path) -> str:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE accounts (user_id CHAR(36) PRIMARY KEY, email VARCHAR(255), phone VARCHAR(20));
        CREATE TABLE test_drive_bookings (id CHAR(36) PRIMARY KEY, customer_phone VARCHAR, vehicle_name VARCHAR);
        """
    )
    owner, twin_a, twin_b = (str(uuid.uuid4()) for _ in range(3))
    connection.executemany(
        "INSERT INTO accounts VALUES (?, ?, ?)",
        [(owner, "owner@example.com", "0911000001"), (twin_a, "a@example.com", "0911000002"), (twin_b, "b@example.com", "0911000002")],
    )
    connection.executemany(
        "INSERT INTO test_drive_bookings VALUES (?, ?, ?)",
        [("b-owned", "0911000001", "VF 6"), ("b-ambiguous", "0911000002", "VF 7"), ("b-guest", "0999999999", "VF 8")],
    )
    connection.commit()
    connection.close()
    return owner


def test_booking_owner_is_backfilled_only_when_unambiguous(workdir):
    path = workdir / "legacy.db"
    owner = legacy_database(path)
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    with engine.begin() as connection:
        run_migrations(connection)
        run_migrations(connection)  # idempotent

    with engine.connect() as connection:
        owners = dict(connection.exec_driver_sql("SELECT id, user_id FROM test_drive_bookings").all())
        indexes = {index["name"] for index in inspect(connection).get_indexes("accounts")}
    engine.dispose()

    assert owners == {"b-owned": owner, "b-ambiguous": None, "b-guest": None}
    # Duplicate phones exist, so the unique index is deferred instead of failing start-up.
    assert "ix_accounts_phone" not in indexes


def test_unique_phone_index_is_added_when_data_allows(workdir):
    path = workdir / "clean.db"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE accounts (user_id CHAR(36) PRIMARY KEY, email VARCHAR(255), phone VARCHAR(20));
        CREATE TABLE test_drive_bookings (id CHAR(36) PRIMARY KEY, customer_phone VARCHAR, user_id CHAR(36));
        INSERT INTO accounts VALUES ('1', 'a@example.com', '0911000001');
        """
    )
    connection.close()
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    with engine.begin() as sa_connection:
        run_migrations(sa_connection)
    with engine.connect() as sa_connection:
        indexes = {index["name"]: index for index in inspect(sa_connection).get_indexes("accounts")}
    engine.dispose()
    assert indexes["ix_accounts_phone"]["unique"]
