# app/core/pdf_generator.py

import uuid
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML
from app.models import Invoice

# Definir ruta absoluta a la carpeta raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# Carpeta donde se guardan los recibos PDF
PDF_STORAGE_DIR = BASE_DIR / "generated_receipts"
PDF_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Inicializar Jinja2 para cargar plantillas desde la carpeta `templates`
TEMPLATES_DIR = BASE_DIR / "templates"
# Asegúrate de crear la carpeta `templates/` y un archivo `receipt.html`
env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"])
)


def generate_pdf(invoice: Invoice) -> tuple[str, str]:
    """
    Genera un PDF real usando WeasyPrint a partir de una plantilla HTML.
    Devuelve:
      - La ruta ABSOLUTA al fichero PDF
      - Una firma simulada (uuid corto)
    """
    # Datos para la plantilla
    data = {
        "invoice_id": invoice.id,
        "cliente": invoice.customer_name or "N/A",
        "monto_msat": invoice.amount_msat,
        "descripcion": invoice.description,
        "payment_hash": invoice.payment_hash,
        "firma": str(uuid.uuid4())[:16]
    }

    # Cargar y renderizar la plantilla
    template = env.get_template("receipt.html")
    html_content = template.render(**data)

    # Generar nombre de archivo y ruta
    filename = f"{invoice.id}.pdf"
    pdf_path = PDF_STORAGE_DIR / filename

    # Usar WeasyPrint para escribir el PDF
    HTML(string=html_content).write_pdf(target=str(pdf_path))

    return str(pdf_path), data["firma"]
