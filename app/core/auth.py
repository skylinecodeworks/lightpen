# app/core/auth.py

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models import APIKey

async def verify_api_key(request: Request, call_next):
    # Rutas públicas
    if request.url.path.startswith("/docs") or request.url.path.startswith("/openapi.json"):
        return await call_next(request)

    key = request.headers.get("x-api-key")
    if not key:
        return JSONResponse(status_code=401, content={"error": "Missing API Key"})

    # Obtener sesión de DB
    db: Session = next(get_db())
    api_key = (
        db.query(APIKey)
          .filter(APIKey.key_hash == key, APIKey.is_active.is_(True))
          .first()
    )
    db.close()

    if not api_key:
        return JSONResponse(status_code=401, content={"error": "Invalid API Key"})

    # inyectamos tenant_id en request.state para los endpoints
    request.state.tenant_id = api_key.tenant_id
    return await call_next(request)


def get_current_tenant(request: Request) -> str:
    return getattr(request.state, "tenant_id", None)
