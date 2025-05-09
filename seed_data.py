# seed_data.py

# 1) Cargamos .env para que DATABASE_URL esté disponible antes de cualquier import
from dotenv import load_dotenv
load_dotenv()

from datetime import datetime, timedelta
from app.core.db import SessionLocal, init_db
from app.models import Tenant, APIKey, Invoice, Receipt

def seed():
    # 2) Crea tablas si hacen falta
    init_db()

    db = SessionLocal()
    try:
        # 3) Crear tenant de prueba
        tenant = Tenant(
            name="Acme Corp",
            email="admin@acme.local",
            plan="monthly",
            next_billing=datetime.utcnow() + timedelta(days=30),
            is_active=True
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        # 4) Generar API key de prueba
        api_key = APIKey(
            tenant_id=tenant.id,
            key_hash="test-key-123",
            expires_at=datetime.utcnow() + timedelta(days=90),
            is_active=True
        )
        db.add(api_key)
        db.commit()

        # 5) Crear una factura y su recibo
        invoice = Invoice(
            tenant_id=tenant.id,
            payment_hash="0000abcd1234",
            amount_msat=150000,
            description="Pago de prueba",
            customer_name="Cliente Demo",
            status="paid"
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)

        receipt = Receipt(
            invoice_id=invoice.id,
            pdf_url=f"./generated_receipts/{invoice.id}.pdf",
            signature="dummy-sign-5678"
        )
        db.add(receipt)
        db.commit()

        print("✅ Datos de prueba creados:")
        print(f"   Tenant.id:  {tenant.id}")
        print(f"   APIKey:     {api_key.key_hash}")
        print(f"   Invoice.id: {invoice.id}")
        print(f"   Receipt.id: {receipt.id}")

    finally:
        db.close()

if __name__ == "__main__":
    seed()
