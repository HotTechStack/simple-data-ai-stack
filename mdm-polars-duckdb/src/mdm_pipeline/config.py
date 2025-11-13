"""Static configuration for the MDM pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data_sources"
ARTIFACTS_DIR = BASE_DIR / "artifacts"


SOURCE_FILES = {
    "billing_system": DATA_DIR / "billing_customers.csv",
    "crm_system": DATA_DIR / "crm_customers.csv",
    "erp_exports": DATA_DIR / "erp_customers.jsonl",
    "finance_excel": DATA_DIR / "finance_customers.xlsx",
    "marketing_automation": DATA_DIR / "marketing_contacts.csv",
    "support_desk": DATA_DIR / "support_customers.csv",
    "legacy_duckdb": DATA_DIR / "legacy_customers.duckdb",
}

SOURCE_PRIORITIES: dict[str, int] = {
    "billing_system": 3,
    "crm_system": 2,
    "erp_exports": 2,
    "finance_excel": 1,
    "marketing_automation": 1,
    "support_desk": 1,
    "legacy_duckdb": 0,
}


COLUMN_ALIASES: dict[str, list[str]] = {
    "customer_id": ["customer_id", "cust_id", "CustomerID", "CustomerId"],
    "customer_name": [
        "customer_name",
        "cust_name",
        "CustomerName",
        "customer_full_name",
    ],
    "email": ["email", "customer_email", "emailAddress", "contact_email"],
    "phone": ["phone", "phone_number", "contact_phone", "phoneNumber"],
    "address": ["address", "mailing_address", "addr", "street_address"],
    "country": ["country", "CountryCode", "country_code"],
    "updated_at": ["updated_at", "last_update", "last_touch", "modified_at"],
}

ISO_COUNTRY_MAP = {
    "United States": "US",
    "USA": "US",
    "U.S.": "US",
    "Germany": "DE",
    "Deutschland": "DE",
    "France": "FR",
    "Spain": "ES",
    "España": "ES",
    "Canada": "CA",
    "CA": "CA",
    "ES": "ES",
    "US": "US",
    "DE": "DE",
    "FR": "FR",
    "UK": "GB",
    "United Kingdom": "GB",
}

HIGH_TRUST_SOURCES = ("billing_system", "crm_system", "erp_exports")

FUZZY_MATCH_THRESHOLD = 85


def utcnow() -> datetime:
    """Return timezone-aware utcnow so audit columns are consistent."""
    return datetime.now(timezone.utc)
