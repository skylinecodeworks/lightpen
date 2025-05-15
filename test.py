import os
import time
import requests
import base64
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


def wait_for_lightpen(timeout=10):
    print(f"⏳ Esperando que Lightpen esté disponible en {API_URL}...")
    for i in range(timeout):
        try:
            r = requests.post(f"{API_URL}/invoices/", timeout=2)
            if r.status_code in [401, 422]:
                print("🟢 Lightpen responde")
                return
        except requests.ConnectionError:
            print(f"  → Intento {i+1}/{timeout}: aún no disponible...")
        time.sleep(1)
    print(f"❌ No se pudo conectar a Lightpen en {API_URL}")
    exit(1)


def is_invoice_settled(payment_hash_hex: str) -> bool:
    url = f"{LND1_REST}/v1/invoice/{payment_hash_hex}"
    r = requests.get(url, headers=MACAROON_LND1, verify=TLS_CERT_PATH)
    r.raise_for_status()
    data = r.json()
    return data.get("settled", False)


def create_invoice_lnd1():
    print("📜 Creando invoice en lnd1...")
    payload = {
        "value_msat": 500000,
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
    print("📜 Recibo generado:", data)
    return data


def wait_for_payment_confirmation(payment_hash, max_attempts=10):
    for attempt in range(max_attempts):
        print(f"🔁 Intentando registrar pago ({attempt+1}/{max_attempts})...")
        try:
            data = call_lightpen_api(payment_hash)
            print("✅ Recibo generado con éxito")
            return data
        except requests.HTTPError as e:
            if e.response.status_code == 400 and "Pago no confirmado" in e.response.text:
                time.sleep(2)
                continue
            raise
    print("❌ El pago no fue reconocido por Lightpen a tiempo.")
    exit(1)


def download_receipt(receipt_url):
    print(f"📅 Descargando PDF desde: {receipt_url}")
    r = requests.get(receipt_url, headers=HEADERS)
    if r.status_code == 200:
        with open("recibo_test.pdf", "wb") as f:
            f.write(r.content)
        print("✅ Recibo guardado como recibo_test.pdf")
    else:
        print("⚠️ No se pudo descargar el recibo:", r.status_code)


if __name__ == "__main__":
    wait_for_lightpen()

    r_hash_raw, payment_request = create_invoice_lnd1()

    if isinstance(r_hash_raw, str):
        payment_hash_hex = base64.b64decode(r_hash_raw).hex()
        payment_hash_b64 = r_hash_raw
    else:
        payment_hash_hex = r_hash_raw.hex()
        payment_hash_b64 = base64.b64encode(r_hash_raw).decode()

    print("🧠 Enviando payment_hash a Lightpen:", payment_hash_hex)
    print("🔍 Consultando estado con payment_hash (base64):", payment_hash_b64)


    pay_invoice_lnd2(payment_request)

    for i in range(10):
        if is_invoice_settled(payment_hash_b64):
            print(f"✅ Invoice settled en intento {i+1}")
            break
        time.sleep(2)
    else:
        print("❌ El pago no fue settled en LND1 a tiempo.")
        exit(1)

    print("⏳ Esperando que el pago sea reconocido por lightpen...")
    data = wait_for_payment_confirmation(payment_hash_b64, max_attempts=10)

    if data.get("receipt_url"):
        download_receipt(data["receipt_url"])
