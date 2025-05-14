import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "http://localhost:8000"
API_KEY = os.getenv("LIGHTPEN_API_KEY", "test-key-123")
HEADERS = {"x-api-key": API_KEY}
LND1_REST = "https://localhost:8080"
LND2_REST = "https://localhost:8081"

TLS_CERT_PATH = os.getenv("LND_TLS_CERT_PATH")

def get_macaroon(path):
    with open(path, "rb") as f:
        return f.read().hex()

MACAROON_LND1 = {"Grpc-Metadata-macaroon": get_macaroon("./docker/lnd/lnd1-data/data/chain/bitcoin/regtest/admin.macaroon")}
MACAROON_LND2 = {"Grpc-Metadata-macaroon": get_macaroon("./docker/lnd/lnd2-data/data/chain/bitcoin/regtest/admin.macaroon")}

def create_invoice_lnd1():
    print("🧾 Creando invoice en lnd1...")
    payload = {
        "value_msat": 500000,  # 500 satoshis
        "memo": "Prueba desde test_lightpen_api"
    }
    r = requests.post(f"{LND1_REST}/v1/invoices", json=payload, headers=MACAROON_LND1, verify=TLS_CERT_PATH)
    r.raise_for_status()
    data = r.json()
    print("📦 Invoice:", data["payment_request"])
    return data["r_hash"], data["payment_request"]

def pay_invoice_lnd2(payment_request):
    print("💸 Pagando invoice desde lnd2...")
    payload = {"payment_request": payment_request}
    r = requests.post(f"{LND2_REST}/v1/channels/transactions", json=payload, headers=MACAROON_LND2, verify=False)
    r.raise_for_status()
    data = r.json()
    print("✅ Pago enviado:", data.get("payment_error") or "sin error")

def call_lightpen_api(payment_hash):
    print("📡 Llamando a /invoices/ de lightpen...")
    payload = {
        "payment_hash": payment_hash,
        "amount_msat": 500_000,
        "description": "Recibo de prueba",
        "customer_name": "Cliente Test"
    }
    r = requests.post(f"{API_URL}/invoices/", json=payload, headers=HEADERS)
    if r.status_code != 200:
        print("❌ Error al llamar a /invoices/")
        print(f"Status: {r.status_code}")
        print("Response:", r.text)
        r.raise_for_status()
    data = r.json()
    print("🧾 Recibo generado:", data)
    return data


def download_receipt(receipt_url):
    print(f"📥 Descargando PDF desde: {receipt_url}")
    r = requests.get(receipt_url, headers=HEADERS)
    if r.status_code == 200:
        with open("recibo_test.pdf", "wb") as f:
            f.write(r.content)
        print("✅ Recibo guardado como recibo_test.pdf")
    else:
        print("⚠️ No se pudo descargar el recibo:", r.status_code)

if __name__ == "__main__":
    r_hash_bytes, payment_request = create_invoice_lnd1()
    if isinstance(r_hash_bytes, str):
        payment_hash = r_hash_bytes.encode("latin1").hex()
    else:
        payment_hash = r_hash_bytes.hex()

    pay_invoice_lnd2(payment_request)

    print("⏳ Esperando que el pago sea reconocido por lightpen...")
    time.sleep(4)

    data = call_lightpen_api(payment_hash)
    if data.get("receipt_url"):
        download_receipt(data["receipt_url"])
