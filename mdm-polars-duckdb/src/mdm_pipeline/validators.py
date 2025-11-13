"\"\"Pandera schemas for catching bad upstream data early.\"\"\""

from __future__ import annotations

import pandera as pa
from pandera import Check, Column, DataFrameSchema

CUSTOMER_SCHEMA = DataFrameSchema(
    {
        "customer_id": Column(pa.String, required=True),
        "customer_name": Column(pa.String, nullable=True),
        "email": Column(
            pa.String,
            nullable=True,
            checks=Check.str_contains("@", ignore_na=True),
        ),
        "phone": Column(pa.String, nullable=True),
        "address": Column(pa.String, nullable=True),
        "country": Column(pa.String, nullable=True),
        "updated_at": Column(pa.DateTime, nullable=True),
    },
    coerce=True,
)
