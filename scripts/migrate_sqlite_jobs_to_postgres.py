#!/usr/bin/env python3
"""Migrate LearnFlow job rows from a local SQLite database to PostgreSQL."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from app.repositories.errors import DuplicateJobError
from app.repositories.postgres import PostgresJobRepository
from app.repositories.sqlite import _row_to_job


def migrate(
    sqlite_path: str | Path,
    database_url: str,
    *,
    skip_existing: bool = False,
) -> tuple[int, int]:
    source = Path(sqlite_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"SQLite source database not found: {source}")

    target = PostgresJobRepository(database_url)
    migrated = 0
    skipped = 0

    conn = sqlite3.connect(str(source))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at ASC").fetchall()
    finally:
        conn.close()

    for row in rows:
        job = _row_to_job(row)
        try:
            target.create(job)
        except DuplicateJobError:
            if not skip_existing:
                raise
            skipped += 1
            continue
        migrated += 1

    return migrated, skipped


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Copy LearnFlow jobs from SQLite to PostgreSQL."
    )
    parser.add_argument(
        "--sqlite",
        required=True,
        help="Path to the existing SQLite database.",
    )
    parser.add_argument(
        "--database-url",
        required=True,
        help="Target PostgreSQL DATABASE_URL. The value is never printed.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip job IDs already present in PostgreSQL.",
    )
    args = parser.parse_args()

    migrated, skipped = migrate(
        args.sqlite,
        args.database_url,
        skip_existing=args.skip_existing,
    )
    print(f"POSTGRES_MIGRATION=PASS migrated={migrated} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
