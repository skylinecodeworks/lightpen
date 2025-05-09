import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.schemas import InvoiceCreate, InvoiceResponse
from app.models import Invoice, Receipt
from app.core.auth import get_current_tenant
from app.services.lnd import check_payment
from app.core.pdf_generator import generate_pdf
from app.core.db import get_db

# Configuramos logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter()

@router.post("/", response_model=InvoiceResponse, tags=["Invoices"])
def create_invoice(
    payload: InvoiceCreate,
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    logger.info(f"→ create_invoice payload recibido: {payload}")

    # 1) Comprobamos si ya existe invoice para este payment_hash + tenant
    existing = (
        db.query(Invoice)
          .filter(
              Invoice.payment_hash == payload.payment_hash,
              Invoice.tenant_id == tenant_id
          )
          .first()
    )
    if existing:
        logger.info(f"↪ Invoice existente encontrada: {existing.id}")
        receipt = (
            db.query(Receipt)
              .filter(Receipt.invoice_id == existing.id)
              .first()
        )
        return InvoiceResponse(
            invoice_id=existing.id,
            status=existing.status,
            receipt_id=receipt.id if receipt else None,
            receipt_url=receipt.pdf_url if receipt else None
        )

    # 2) Verificamos en LND que el pago esté confirmado
    if not check_payment(payload.payment_hash):
        logger.warning(f"Pago no confirmado para hash {payload.payment_hash}")
        raise HTTPException(status_code=400, detail="Pago no confirmado")

    # 3) Creamos la nueva invoice
    invoice = Invoice(
        tenant_id=tenant_id,
        payment_hash=payload.payment_hash,
        amount_msat=payload.amount_msat,
        description=payload.description,
        customer_name=payload.customer_name,
        status="paid"
    )
    db.add(invoice)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.error(f"Violación de clave única: {payload.payment_hash}")
        raise HTTPException(status_code=409, detail="Invoice ya existe")
    db.refresh(invoice)
    logger.info(f"✔ Invoice creada con id {invoice.id}")

    # 4) Generamos el PDF y la firma
    pdf_url, signature = generate_pdf(invoice)
    logger.info(f"✓ PDF generado en {pdf_url}, firma={signature}")

    # 5) Guardamos el receipt
    receipt = Receipt(
        invoice_id=invoice.id,
        pdf_url=pdf_url,
        signature=signature
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    logger.info(f"✔ Receipt creado con id {receipt.id}")

    # 6) Devolvemos la respuesta final
    return InvoiceResponse(
        invoice_id=invoice.id,
        status=invoice.status,
        receipt_id=receipt.id,
        receipt_url=pdf_url
    )
