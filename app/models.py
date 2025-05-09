# app/models.py

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Text
from app.core.db import Base

def gen_id():
    return str(uuid.uuid4())

class Tenant(Base):
    __tablename__ = "tenants"
    id           = Column(String,   primary_key=True, default=gen_id)
    name         = Column(String,   nullable=False)
    email        = Column(String,   nullable=False, unique=True)
    plan         = Column(String,   nullable=False, default="free")  # free, monthly, yearly
    next_billing = Column(DateTime)
    is_active    = Column(Boolean,  default=True)
    created_at   = Column(DateTime, default=datetime.utcnow)

class APIKey(Base):
    __tablename__ = "api_keys"
    id         = Column(String,   primary_key=True, default=gen_id)
    tenant_id  = Column(String,   ForeignKey("tenants.id"), nullable=False)
    key_hash   = Column(String,   nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    is_active  = Column(Boolean,  default=True)

class Invoice(Base):
    __tablename__ = "invoices"
    id            = Column(String,   primary_key=True, default=gen_id)
    tenant_id     = Column(String,   ForeignKey("tenants.id"), nullable=False)
    payment_hash  = Column(String,   unique=True,  nullable=False)
    amount_msat   = Column(Integer,  nullable=False)
    description   = Column(Text)
    customer_name = Column(String)
    status        = Column(String,   default="pending")  # paid, expired
    created_at    = Column(DateTime, default=datetime.utcnow)

class Receipt(Base):
    __tablename__ = "receipts"
    id           = Column(String,   primary_key=True, default=gen_id)
    invoice_id   = Column(String,   ForeignKey("invoices.id"), nullable=False)
    pdf_url      = Column(String)
    signature    = Column(String)
    generated_at = Column(DateTime, default=datetime.utcnow)
