"""Copy the local pilot data from PostgreSQL to the canonical MySQL schema.

Run only after `backup-postgres.ps1` and `bootstrap-mysql.ps1` succeed.
The script preserves primary keys and aborts rather than truncating URLs that
cannot be represented by MySQL's indexed `news_articles.source_url` column.
"""

from __future__ import annotations

import os
from collections.abc import Iterable

from sqlalchemy import MetaData, create_engine, insert, select, text


POSTGRES_URL = os.getenv(
    "POSTGRES_SOURCE_URL",
    "postgresql+psycopg2://autoridad:autoridadpass@127.0.0.1:5433/autoridad360",
)
MYSQL_URL = os.getenv(
    "MYSQL_TARGET_URL",
    "mysql+pymysql://autoridad:autoridadpass@127.0.0.1:3307/autoridad360",
)
BATCH_SIZE = 200
EXCLUDED_TABLES = {"alembic_version"}


def batches(rows: Iterable[dict], size: int = BATCH_SIZE):
    batch: list[dict] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def main() -> None:
    source = create_engine(POSTGRES_URL)
    target = create_engine(MYSQL_URL)
    source_meta = MetaData()
    target_meta = MetaData()
    source_meta.reflect(bind=source)
    target_meta.reflect(bind=target)

    table_names = sorted(
        set(source_meta.tables) & set(target_meta.tables) - EXCLUDED_TABLES
    )
    with source.connect() as source_conn, target.begin() as target_conn:
        long_urls = source_conn.execute(
            text("SELECT id, source_url FROM news_articles WHERE char_length(source_url) > 767")
        ).mappings().all()
        if long_urls:
            ids = ", ".join(str(row["id"]) for row in long_urls[:10])
            raise RuntimeError(
                f"{len(long_urls)} URL(s) exceed the MySQL indexed limit (first ids: {ids}). "
                "Resolve them before migration; no data was copied."
            )

        target_conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        try:
            for name in reversed(table_names):
                target_conn.execute(target_meta.tables[name].delete())

            for name in table_names:
                source_table = source_meta.tables[name]
                target_table = target_meta.tables[name]
                target_columns = {column.name for column in target_table.columns}
                result = source_conn.execute(select(source_table)).mappings()
                copied = 0
                for batch in batches(
                    ({key: value for key, value in row.items() if key in target_columns} for row in result)
                ):
                    target_conn.execute(insert(target_table), batch)
                    copied += len(batch)
                print(f"{name}: {copied}")

            target_conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        except Exception:
            target_conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            raise

    print("Migracion PostgreSQL -> MySQL completada.")


if __name__ == "__main__":
    main()
