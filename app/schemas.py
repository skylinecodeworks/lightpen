from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class InvoiceCreate(BaseModel):
    payment_hash: str
    amount_msat: int
    description: str
    customer_name: Optional[str] = None

class InvoiceResponse(BaseModel):
    invoice_id: str
    status: str
    receipt_id: Optional[str] = None
    receipt_url: Optional[str] = None
