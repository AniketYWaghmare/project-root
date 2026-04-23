import httpx
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from models.customer import Customer

FLASK_BASE_URL = "http://mock-server:5000"


async def fetch_all_customers() -> list[dict]:
    """Fetch all customers from Flask API, handling pagination automatically."""
    all_customers = []
    page = 1
    limit = 50  # fetch in chunks

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            response = await client.get(
                f"{FLASK_BASE_URL}/api/customers",
                params={"page": page, "limit": limit},
            )
            response.raise_for_status()
            payload = response.json()

            data = payload.get("data", [])
            all_customers.extend(data)

            total = payload.get("total", 0)
            if len(all_customers) >= total or not data:
                break

            page += 1

    return all_customers


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _parse_datetime(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def upsert_customers(db: Session, customers: list[dict]) -> int:
    """Upsert customer records into PostgreSQL. Returns number of records processed."""
    if not customers:
        return 0

    rows = [
        {
            "customer_id": c["customer_id"],
            "first_name": c["first_name"],
            "last_name": c["last_name"],
            "email": c["email"],
            "phone": c.get("phone"),
            "address": c.get("address"),
            "date_of_birth": _parse_date(c.get("date_of_birth")),
            "account_balance": Decimal(str(c["account_balance"])) if c.get("account_balance") is not None else None,
            "created_at": _parse_datetime(c.get("created_at")),
        }
        for c in customers
    ]

    stmt = pg_insert(Customer).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["customer_id"],
        set_={
            "first_name": stmt.excluded.first_name,
            "last_name": stmt.excluded.last_name,
            "email": stmt.excluded.email,
            "phone": stmt.excluded.phone,
            "address": stmt.excluded.address,
            "date_of_birth": stmt.excluded.date_of_birth,
            "account_balance": stmt.excluded.account_balance,
            "created_at": stmt.excluded.created_at,
        },
    )

    db.execute(stmt)
    db.commit()
    return len(rows)
