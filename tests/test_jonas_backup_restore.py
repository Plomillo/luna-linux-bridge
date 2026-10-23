import sqlite3

import pytest

from scripts.missions.backup_restore_jonas_state import backup, check_integrity, restore, sha256_file


def make_db(path, value):
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS sample (value INTEGER NOT NULL)")
        conn.execute("DELETE FROM sample")
        conn.execute("INSERT INTO sample(value) VALUES (?)", (value,))


def read_value(path):
    with sqlite3.connect(path) as conn:
        return conn.execute("SELECT value FROM sample").fetchone()[0]


def test_backup_restore_preserves_checkpoint_and_integrity(tmp_path):
    database = tmp_path / "jonas.sqlite3"
    backup_file = tmp_path / "jonas-backup.sqlite3"
    make_db(database, 42)

    manifest = backup(database, backup_file)
    assert manifest["integrity_check"] == "ok"
    assert manifest["sha256"] == sha256_file(backup_file)
    assert backup_file.with_suffix(".sqlite3.json").is_file()
    assert backup_file.with_suffix(".sqlite3.sha256").is_file()

    make_db(database, 99)
    restored = restore(
        backup_file, database, manifest["sha256"],
        confirm_restore=True, service_stopped_confirmed=True,
    )
    assert read_value(database) == 42
    assert restored["integrity_check"] == "ok"
    assert restored["pre_restore_checkpoint"] is not None
    assert read_value(__import__("pathlib").Path(restored["pre_restore_checkpoint"])) == 99
    check_integrity(database)


def test_restore_fails_closed_without_explicit_authorization(tmp_path):
    database = tmp_path / "jonas.sqlite3"
    backup_file = tmp_path / "backup.sqlite3"
    make_db(database, 7)
    manifest = backup(database, backup_file)

    with pytest.raises(PermissionError, match="confirm-restore"):
        restore(
            backup_file, database, manifest["sha256"],
            confirm_restore=False, service_stopped_confirmed=True,
        )
    with pytest.raises(PermissionError, match="service-stopped-confirmed"):
        restore(
            backup_file, database, manifest["sha256"],
            confirm_restore=True, service_stopped_confirmed=False,
        )
    assert read_value(database) == 7


def test_restore_rejects_hash_mismatch_before_modifying_target(tmp_path):
    database = tmp_path / "jonas.sqlite3"
    backup_file = tmp_path / "backup.sqlite3"
    make_db(database, 7)
    backup(database, backup_file)

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        restore(
            backup_file, database, "0" * 64,
            confirm_restore=True, service_stopped_confirmed=True,
        )
    assert read_value(database) == 7
