from __future__ import annotations

import json

import asyncpg
from typing import Any, Dict


class MetadataStore:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(dsn=self._dsn, min_size=1, max_size=5)

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    async def record_success(
        self,
        *,
        source_name: str,
        source_type: str,
        run_id: str,
        raw_object_key: str,
        processed_object_key: str,
        row_count: int,
        schema: Dict[str, Any],
    ) -> None:
        if not self._pool:
            raise RuntimeError("MetadataStore is not connected")

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                schema_hash = schema["hash"]
                version_row = await conn.fetchrow(
                    """
                    SELECT version
                    FROM ingestion_schemas
                    WHERE source_name = $1 AND schema_hash = $2
                    """,
                    source_name,
                    schema_hash,
                )

                if version_row:
                    schema_version = version_row["version"]
                else:
                    next_version_row = await conn.fetchrow(
                        """
                        SELECT COALESCE(MAX(version), 0) + 1 AS next_version
                        FROM ingestion_schemas
                        WHERE source_name = $1
                        """,
                        source_name,
                    )
                    schema_version = next_version_row["next_version"]
                    await conn.execute(
                        """
                        INSERT INTO ingestion_schemas (source_name, version, schema_hash, schema)
                        VALUES ($1, $2, $3, $4::jsonb)
                        """,
                        source_name,
                        schema_version,
                        schema_hash,
                        json.dumps(schema["columns"]),
                    )

                await conn.execute(
                    """
                    INSERT INTO ingestion_runs (
                        source_name,
                        source_type,
                        run_id,
                        raw_object_key,
                        processed_object_key,
                        row_count,
                        schema_version,
                        schema_hash
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (source_name) DO UPDATE
                    SET run_id = EXCLUDED.run_id,
                        source_type = EXCLUDED.source_type,
                        raw_object_key = EXCLUDED.raw_object_key,
                        processed_object_key = EXCLUDED.processed_object_key,
                        row_count = EXCLUDED.row_count,
                        schema_version = EXCLUDED.schema_version,
                        schema_hash = EXCLUDED.schema_hash,
                        succeeded_at = NOW()
                    """,
                    source_name,
                    source_type,
                    run_id,
                    raw_object_key,
                    processed_object_key,
                    row_count,
                    schema_version,
                    schema_hash,
                )

    async def record_failure(
        self,
        *,
        source_name: str,
        source_type: str,
        run_id: str,
        attempt: int,
        error: str,
        payload: Dict[str, Any],
    ) -> None:
        if not self._pool:
            raise RuntimeError("MetadataStore is not connected")

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO ingestion_failures (
                    source_name, source_type, run_id, attempt, error, payload
                )
                VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                """,
                source_name,
                source_type,
                run_id,
                attempt,
                error,
                json.dumps(payload),
            )

    async def fetch_health(self) -> Dict[str, Any]:
        if not self._pool:
            raise RuntimeError("MetadataStore is not connected")

        async with self._pool.acquire() as conn:
            runs = await conn.fetchrow("SELECT COUNT(*) AS total_runs FROM ingestion_runs")
            failures = await conn.fetchrow(
                "SELECT COUNT(*) AS total_failures FROM ingestion_failures WHERE created_at > NOW() - INTERVAL '1 day'"
            )
            return {
                "total_runs": runs["total_runs"],
                "failures_last_day": failures["total_failures"],
            }
