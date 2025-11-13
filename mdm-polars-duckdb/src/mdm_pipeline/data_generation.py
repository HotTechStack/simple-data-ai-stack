"""Create synthetic source files that mimic messy upstream systems."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import duckdb
import polars as pl

from .config import DATA_DIR, SOURCE_FILES

BASE_CUSTOMERS = [
    {
        "customer_id": "CUST-001",
        "customer_name": "Alice Johnson",
        "email": "alice.johnson@example.com",
        "phone": "+1 415 555 0101",
        "address": "123 Market St, San Francisco, CA",
        "country": "United States",
        "updated_at": "2024-05-18T12:30:00Z",
    },
    {
        "customer_id": "CUST-002",
        "customer_name": "Brian Müller",
        "email": "brian.mueller@example.com",
        "phone": "+49 30 1234 9876",
        "address": "Unter den Linden 5, Berlin",
        "country": "Germany",
        "updated_at": "2024-05-10T09:20:00Z",
    },
    {
        "customer_id": "CUST-003",
        "customer_name": "Carla Lopes",
        "email": "carla.lopes@example.com",
        "phone": "+33 1 22 33 44 55",
        "address": "10 Rue Oberkampf, Paris",
        "country": "France",
        "updated_at": "2023-11-02T08:00:00Z",
    },
    {
        "customer_id": "CUST-004",
        "customer_name": "Diego Fernández",
        "email": "diego.fernandez@example.com",
        "phone": "+34 91 123 45 67",
        "address": "Gran Via 45, Madrid",
        "country": "Spain",
        "updated_at": "2022-09-14T18:40:00Z",
    },
    {
        "customer_id": "CUST-005",
        "customer_name": "Emily Clark",
        "email": "emily.clark@example.com",
        "phone": "+1 617 555 0182",
        "address": "77 Massachusetts Ave, Boston, MA",
        "country": "USA",
        "updated_at": "2024-01-05T14:00:00Z",
    },
    {
        "customer_id": "CUST-006",
        "customer_name": "Farid Khan",
        "email": "farid.khan@example.com",
        "phone": "+44 20 7946 0999",
        "address": "221B Baker Street, London",
        "country": "United Kingdom",
        "updated_at": "2019-06-12T07:15:00Z",
    },
]


def _date(offset_days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=offset_days)).isoformat()


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _write_csv(path: Path, rows: Iterable[dict]) -> None:
    pl.DataFrame(rows).write_csv(path)


def _write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row))
            f.write("\n")


def _write_excel(path: Path, rows: Iterable[dict]) -> None:
    pl.DataFrame(rows).write_excel(path, worksheet="finance")


def _write_duckdb(path: Path, rows: Iterable[dict]) -> None:
    con = duckdb.connect(str(path))
    df = pl.DataFrame(rows).to_arrow()
    con.execute("DROP TABLE IF EXISTS legacy_customers")
    con.execute("CREATE TABLE legacy_customers AS SELECT * FROM df")
    con.close()


def generate_sample_sources() -> None:
    """Write all seven messy sources so the pipeline can read them."""
    _ensure_dirs()

    billing_rows = []
    crm_rows = []
    erp_rows = []
    finance_rows = []
    marketing_rows = []
    support_rows = []
    legacy_rows = []

    for idx, base in enumerate(BASE_CUSTOMERS, start=1):
        billing_rows.append(
            {
                "customer_id": base["customer_id"],
                "customer_name": base["customer_name"],
                "email": base["email"],
                "phone": base["phone"],
                "address": base["address"],
                "country": base["country"],
                "updated_at": base["updated_at"],
            }
        )

        crm_row = {
            "CustomerID": base["customer_id"],
            "CustomerName": base["customer_name"].upper() if idx % 2 == 0 else base["customer_name"],
            "emailAddress": base["email"].replace("@example.com", "@corp.test"),
            "phone_number": base["phone"].replace(" ", ""),
            "mailing_address": base["address"],
            "CountryCode": base["country"],
            "last_update": _date(30 + idx),
        }
        if base["customer_id"] == "CUST-003":
            crm_row["emailAddress"] = "c.lopes+crm@example.net"
        crm_rows.append(crm_row)

        erp_rows.append(
            {
                "cust_id": base["customer_id"],
                "cust_name": base["customer_name"].replace("í", "i"),
                "contact_email": base["email"].upper(),
                "contact_phone": base["phone"],
                "street_address": base["address"],
                "country_code": base["country"],
                "modified_at": _date(120 + idx),
            }
        )

        finance_rows.append(
            {
                "customer_id": base["customer_id"],
                "customer_full_name": base["customer_name"],
                "email": base["email"],
                "phone": base["phone"],
                "addr": base["address"],
                "country": base["country"],
                "last_touch": base["updated_at"],
                "credit_score": 700 + idx * 5,
            }
        )

        marketing_rows.append(
            {
                "cust_id": base["customer_id"],
                "customer_name": base["customer_name"].replace(" ", ""),
                "email": base["email"].replace("example.com", "marketing.io"),
                "phone": None if idx % 3 == 0 else base["phone"],
                "country": base["country"],
                "updated_at": _date(10 + idx),
            }
        )

        support_rows.append(
            {
                "customer_id": base["customer_id"],
                "customer_name": f"{base['customer_name']} (Support)",
                "contact_email": base["email"],
                "phone": base["phone"],
                "address": base["address"],
                "country": base["country"],
                "updated_at": _date(200 + idx),
                "open_tickets": idx % 2,
            }
        )

        legacy_rows.append(
            {
                "customer_id": base["customer_id"],
                "cust_name": base["customer_name"],
                "email": base["email"],
                "phone": base["phone"],
                "address": base["address"],
                "country": base["country"],
                "updated_at": base["updated_at"],
            }
        )

    marketing_rows.append(
        {
            "cust_id": "TMP-777",
            "customer_name": "Em Clarke",
            "email": "em.clarke@marketing.io",
            "phone": None,
            "country": "Canada",
            "updated_at": _date(2),
        }
    )

    support_rows.append(
        {
            "customer_id": "LEG-888",
            "customer_name": "Emily Clark",
            "contact_email": "emilyc@legacy-data.com",
            "phone": None,
            "address": "Unknown",
            "country": "USA",
            "updated_at": "2017-03-01T00:00:00Z",
            "open_tickets": 3,
        }
    )

    _write_csv(SOURCE_FILES["billing_system"], billing_rows)
    _write_csv(SOURCE_FILES["crm_system"], crm_rows)
    _write_jsonl(SOURCE_FILES["erp_exports"], erp_rows)
    _write_excel(SOURCE_FILES["finance_excel"], finance_rows)
    _write_csv(SOURCE_FILES["marketing_automation"], marketing_rows)
    _write_csv(SOURCE_FILES["support_desk"], support_rows)
    _write_duckdb(SOURCE_FILES["legacy_duckdb"], legacy_rows)

