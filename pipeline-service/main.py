from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db, init_db
from models.customer import Customer
from services.ingestion import fetch_all_customers, upsert_customers


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables on startup
    init_db()
    yield


app = FastAPI(
    title="Customer Data Pipeline",
    description="FastAPI service that ingests customer data from Flask mock server into PostgreSQL.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/api/health")
def health():
    return {"status": "healthy", "service": "pipeline-service"}


@app.post("/api/ingest")
async def ingest(db: Session = Depends(get_db)):
    """
    Fetch all customers from Flask mock server (handles pagination automatically)
    and upsert them into PostgreSQL.
    """
    try:
        customers = await fetch_all_customers()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch data from mock server: {str(e)}")

    try:
        records_processed = upsert_customers(db, customers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database upsert failed: {str(e)}")

    return {"status": "success", "records_processed": records_processed}


@app.get("/api/customers")
def get_customers(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=10, ge=1, le=100, description="Records per page"),
    db: Session = Depends(get_db),
):
    """Return paginated customer records from PostgreSQL."""
    total = db.query(Customer).count()
    offset = (page - 1) * limit
    customers = db.query(Customer).offset(offset).limit(limit).all()

    return {
        "data": [c.to_dict() for c in customers],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total > 0 else 0,
    }


@app.get("/api/customers/{customer_id}")
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    """Return a single customer by ID or 404."""
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer '{customer_id}' not found")
    return {"data": customer.to_dict()}
