# main.py

# 1) Lo primero: cargar el .env
from app.core.config import load_config
load_config()

# 2) Ahora importamos el resto con la certeza de que DATABASE_URL existe
from fastapi import FastAPI
from app.routes import invoices, receipts
from app.core.auth import verify_api_key
from app.core.db import init_db
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

# 3) Inicializar la base de datos (create_all o migraciones)
init_db()

app = FastAPI(
    title="Generador de Recibo Lightning",
    version="0.1.0"
)

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 App arrancada, ready to receive requests")

# Middleware para API Key (usamos el verify_api_key que retorna call_next)
app.middleware("http")(verify_api_key)

# Rutas principales
app.include_router(invoices.router, prefix="/invoices", tags=["Invoices"])
app.include_router(receipts.router, prefix="/receipts", tags=["Receipts"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
