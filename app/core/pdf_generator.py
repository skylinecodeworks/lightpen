# app/core/pdf_generator.py

import uuid
from pathlib import Path
from app.models import Invoice

# Definir ruta absoluta a la carpeta raíz del proyecto
# (__file__) -> .../app/core/pdf_generator.py
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# Carpeta donde se guardan los recibos
PDF_STORAGE_DIR = BASE_DIR / "generated_receipts"
PDF_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def generate_pdf(invoice: Invoice) -> tuple[str, str]:
    """
    Genera un PDF simulado (texto plano) y devuelve:
      - La ruta ABSOLUTA al fichero para FileResponse
      - Una firma simulada
    """
    filename = f"{invoice.id}.pdf"
    pdf_path = PDF_STORAGE_DIR / filename
    signature = str(uuid.uuid4())[:16]

    # Crear contenido del PDF (a sustituir con WeasyPrint más adelante)
    content = (
        "RECIBO LIGHTNING\n\n"
        f"Cliente: {invoice.customer_name or 'N/A'}\n"
        f"Monto (msat): {invoice.amount_msat}\n"
        f"Descripción: {invoice.description}\n"
        f"Hash de pago: {invoice.payment_hash}\n"
        f"Firma: {signature}\n"
    )

    # Escribir el archivo en la ruta absoluta
    with open(pdf_path, "w") as f:
        f.write(content)

    # Retornar ruta absoluta y firma
    return str(pdf_path.resolve()), signature
