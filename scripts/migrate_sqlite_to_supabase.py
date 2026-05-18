from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]
SQLITE_PATH = Path(os.getenv("SQLITE_PATH", ROOT / "sales_ai.sqlite3"))
DATABASE_URL = os.getenv("DATABASE_URL")

TABLES = ["companies", "forms", "proposals", "activities", "send_logs"]


def main() -> None:
    if not DATABASE_URL:
        raise SystemExit("DATABASE_URL is required.")
    if not SQLITE_PATH.exists():
        raise SystemExit(f"SQLite file not found: {SQLITE_PATH}")

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    with psycopg.connect(DATABASE_URL) as pg_conn:
        for table in TABLES:
            migrate_table(sqlite_conn, pg_conn, table)
        pg_conn.commit()

    sqlite_conn.close()
    print("Migration completed.")


def migrate_table(sqlite_conn: sqlite3.Connection, pg_conn, table: str) -> None:
    rows = sqlite_conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
    if not rows:
        print(f"{table}: 0 rows")
        return

    columns = rows[0].keys()
    placeholders = ", ".join(["%s"] * len(columns))
    column_names = ", ".join(columns)

    if table == "companies":
        conflict = """
        ON CONFLICT(name, url) DO UPDATE SET
            industry=excluded.industry,
            area=excluded.area,
            address=excluded.address,
            phone=excluded.phone,
            email=excluded.email,
            contact_url=excluded.contact_url,
            summary=excluded.summary,
            need_score=excluded.need_score,
            score_reason=excluded.score_reason,
            suggested_offer=excluded.suggested_offer,
            status=excluded.status,
            updated_at=excluded.updated_at
        """
    else:
        conflict = "ON CONFLICT DO NOTHING"

    query = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders}) {conflict}"
    with pg_conn.cursor() as cur:
        for row in rows:
            cur.execute(query, tuple(row[column] for column in columns))
        cur.execute(
            """
            SELECT setval(
                pg_get_serial_sequence(%s, 'id'),
                COALESCE((SELECT MAX(id) FROM """ + table + """), 1),
                true
            )
            """,
            (table,),
        )

    print(f"{table}: {len(rows)} rows")


if __name__ == "__main__":
    main()
