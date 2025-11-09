"""Generate fake inserts/updates/deletes to showcase incremental sync."""

from __future__ import annotations

import os
import random
import string
from datetime import datetime

import psycopg
from psycopg.rows import dict_row


def _rand_email() -> str:
    user = ''.join(random.choices(string.ascii_lowercase, k=8))
    return f"{user}@example.com"


def _rand_plan() -> str:
    return random.choice(["free", "starter", "growth", "enterprise"])


def main() -> None:
    dsn = (
        f"host={os.getenv('POSTGRES_HOST', 'postgres')} "
        f"port={os.getenv('POSTGRES_PORT', '5432')} "
        f"dbname={os.getenv('POSTGRES_DB', 'analytics')} "
        f"user={os.getenv('POSTGRES_USER', 'analyst')} "
        f"password={os.getenv('POSTGRES_PASSWORD', 'analyst')}"
    )
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        conn.execute("SET TIME ZONE 'UTC'")
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.subscriptions (email, plan, lifetime_value)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (_rand_email(), _rand_plan(), random.randint(10, 5000)),
            )
            inserted_id = cur.fetchone()["id"]
            cur.execute(
                """
                UPDATE public.subscriptions
                SET plan = 'growth', lifetime_value = lifetime_value + 250
                WHERE id = (SELECT id FROM public.subscriptions WHERE deleted_at IS NULL ORDER BY random() LIMIT 1)
                RETURNING id
                """
            )
            updated = cur.fetchone()
            cur.execute(
                """
                UPDATE public.subscriptions
                SET deleted_at = NOW()
                WHERE id = (
                    SELECT id FROM public.subscriptions
                    WHERE deleted_at IS NULL AND id <> %s
                    ORDER BY random() LIMIT 1
                )
                RETURNING id
                """,
                (inserted_id,),
            )
            deleted = cur.fetchone()
        conn.commit()
    print(
        f"Inserted id={inserted_id}, updated id={updated['id'] if updated else 'n/a'}, deleted id={deleted['id'] if deleted else 'n/a'} at {datetime.utcnow().isoformat()}"
    )


if __name__ == "__main__":
    main()
