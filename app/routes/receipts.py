# app/routes/receipts.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from app.core.auth import get_current_tenant
from app.core.db import get_db
from app.models import Receipt, Invoice

router = APIRouter()

@router.get("/{receipt_id}", response_class=FileResponse, tags=["Receipts"])
def get_receipt(
    receipt_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Devuelve el PDF de un recibo sólo si pertenece al tenant autenticado.
    """
    # Buscamos el recibo asegurando que el invoice asociado pertenece al tenant
    receipt = (
        db.query(Receipt)
          .join(Invoice, Invoice.id == Receipt.invoice_id)
          .filter(Receipt.id == receipt_id,
                  Invoice.tenant_id == tenant_id)
          .first()
    )
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    return FileResponse(
        path=receipt.pdf_url,
        media_type="application/pdf",
        filename=f"{receipt.id}.pdf"
    )
