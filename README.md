# LightPen: Bitcoin Lightning Receipt Generator

Sistema completo para la creación y validación de recibos PDF de pagos realizados a través de la Lightning Network (Bitcoin), utilizando exclusivamente comunicación gRPC con nodos LND (Lightning Network Daemon) y un backend en FastAPI que valida y genera los recibos.

---

## Arquitectura General

- **bitcoind**: nodo de Bitcoin en regtest que provee la red blockchain para pruebas.
- **lnd1**: nodo LND que genera invoices.
- **lnd2**: nodo LND que actúa como pagador.
- **FastAPI backend**: expone un endpoint REST `POST /invoices` que:
  - Verifica si el `payment_hash` corresponde a una invoice pagada.
  - Genera un recibo PDF con firma.
  - Persiste el recibo en base de datos.

---

## Stack Tecnológico

- Python 3.12
- FastAPI
- SQLAlchemy + PostgreSQL
- Docker Compose (con bitcoind y 2 nodos LND)
- `lndgrpc` para interacción vía gRPC
- `requests` para consumo del backend desde el test
- `dotenv` para configuración

---

## Requisitos

- Docker + Docker Compose
- Python 3.12+
- PostgreSQL corriendo en `DATABASE_URL` configurada en `.env`

---

## Configuración

### Variables de entorno `.env`

```dotenv
# Base de datos
DATABASE_URL=postgresql://myuser:mypassword@127.0.0.1:5432/lightning_receipts

# Clave para el endpoint de API
API_KEY=devkey
API_KEY_SALT=change_this_salt

# LND nodo 1 (emisor de invoices)
LND_GRPC_HOST=localhost:10009
LND_MACAROON_PATH=./docker/lnd/lnd1-data/data/chain/bitcoin/regtest/admin.macaroon
LND_TLS_CERT_PATH=./docker/lnd/lnd1-data/tls.cert
LND_NETWORK=regtest

# LND nodo 2 (pagador)
LND2_MACAROON_PATH=./docker/lnd/lnd2-data/data/chain/bitcoin/regtest/admin.macaroon
LND2_TLS_CERT_PATH=./docker/lnd/lnd2-data/tls.cert
````

---

## Puesta en marcha

### 1. Construcción del entorno

```bash
docker-compose down -v
docker-compose up -d
```

### 2. Aplicación FastAPI

```bash
uvicorn main:app --reload
```

---

## Test end-to-end (Lightning + Recibo)

El script `test_grpc_add_invoice.py` automatiza:

1. Conexión entre `lnd2` y `lnd1`.
2. Fondeo de `lnd2` desde `bitcoind` si es necesario.
3. Apertura de canal Lightning.
4. Creación de invoice desde `lnd1` (gRPC).
5. Pago de invoice desde `lnd2` (gRPC).
6. Confirmación de invoice pagada (`settled`).
7. Llamada al backend `POST /invoices` con `payment_hash`.
8. Generación automática del PDF del recibo.

### Ejecución

```bash
uv run test_grpc_add_invoice.py
```

Cabe indicar que la inicialización, fondeo, creación de canales, etc. Se realiza utilizando el script `init_lightning_stack.py`

---

## Endpoint principal del backend

### `POST /invoices`

Registra una invoice ya pagada y genera un recibo en PDF.

#### Headers:

```http
x-api-key: devkey
Content-Type: application/json
```

#### Body:

```json
{
  "payment_hash": "cf2aaec56314002701cdadc1ba6cb699e26977116c1426445fcf5d08f9380615",
  "amount_msat": 500000,
  "description": "Prueba vía gRPC",
  "customer_name": "Test User"
}
```

#### Response:

```json
{
  "invoice_id": 1,
  "status": "paid",
  "receipt_id": 1,
  "receipt_url": "/receipts/1.pdf",
  "signature": "b309f..."
}
```

---

## Verificación del sistema

Puedes verificar manualmente:

```bash
# Verificar estado de sincronización
docker exec -it lnd1 lncli --network=regtest getinfo
docker exec -it lnd2 lncli --network=regtest --rpcserver=localhost:10010 getinfo

# Listar canales y balances
docker exec -it lnd2 lncli --network=regtest --rpcserver=localhost:10010 listchannels
docker exec -it lnd2 lncli --network=regtest --rpcserver=localhost:10010 walletbalance
```

---

## Futuras extensiones

* Test de carga paralela usando ThreadPoolExecutor.
* Exportación de métricas de latencia en JSON o Prometheus.
* Validación de firma de recibos.
* Soporte multi-tenant por header API key.

---

## Créditos

Este proyecto fue construido para demostrar una integración completa de la Lightning Network usando `lndgrpc`, FastAPI y PostgreSQL, con soporte para recibos legales automatizados.

