import os
import time
import requests
import base64
import subprocess
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

API_URL = "http://localhost:8000"
API_KEY = os.getenv("LIGHTPEN_API_KEY", "test-key-123")
HEADERS = {"x-api-key": API_KEY}
LND1_REST = "https://localhost:8080"
LND2_REST = "https://localhost:8081"

TLS_CERT_PATH = os.getenv("LND_TLS_CERT_PATH")
LOGFILE = "lightpen_test_log.txt"


def log_event(text):
    timestamp = datetime.utcnow().isoformat()
    with open(LOGFILE, "a") as f:
        f.write(f"[{timestamp}] {text}\n")


def run_docker_command(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        log_event(f"Comando docker exec exitoso: {' '.join(cmd)}\n{result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        log_event(f"Fallo en comando docker exec: {' '.join(cmd)}\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")


def get_macaroon(path):
    with open(path, "rb") as f:
        return f.read().hex()


MACAROON_LND1 = {"Grpc-Metadata-macaroon": get_macaroon("./docker/lnd/lnd1-data/data/chain/bitcoin/regtest/admin.macaroon")}
MACAROON_LND2 = {"Grpc-Metadata-macaroon": get_macaroon("./docker/lnd/lnd2-data/data/chain/bitcoin/regtest/admin.macaroon")}


def wait_for_lightpen(timeout=10):
    log_event("Esperando disponibilidad de Lightpen")
    print(f"⏳ Esperando que Lightpen esté disponible en {API_URL}...")
    for i in range(timeout):
        try:
            r = requests.post(f"{API_URL}/invoices/", timeout=2)
            if r.status_code in [401, 422]:
                print("🟢 Lightpen responde")
                log_event("Lightpen responde correctamente")
                return
        except requests.ConnectionError:
            print(f"  → Intento {i+1}/{timeout}: aún no disponible...")
            log_event(f"Intento {i+1}: Lightpen no disponible")
        time.sleep(1)
    log_event("No se pudo conectar a Lightpen")
    print(f"❌ No se pudo conectar a Lightpen en {API_URL}")
    exit(1)


def is_invoice_settled(payment_hash_hex: str) -> bool:
    url = f"{LND1_REST}/v1/invoice/{payment_hash_hex}"
    r = requests.get(url, headers=MACAROON_LND1, verify=TLS_CERT_PATH)
    r.raise_for_status()
    data = r.json()
    settled = data.get("settled", False)
    log_event(f"Consulta estado de invoice ({payment_hash_hex}): settled={settled}")
    return settled


def create_invoice_lnd1():
    print("📜 Creando invoice en lnd1...")
    payload = {
        "value_msat": 500000,
        "memo": "Prueba desde test_lightpen_api"
    }
    r = requests.post(f"{LND1_REST}/v1/invoices", json=payload, headers=MACAROON_LND1, verify=TLS_CERT_PATH)
    r.raise_for_status()
    data = r.json()
    log_event(f"Invoice creada: payment_request={data['payment_request']} | r_hash={data['r_hash']}")
    print("📦 Invoice:", data["payment_request"])
    return data["r_hash"], data["payment_request"]


def pay_invoice_lnd2(payment_request):
    print("💸 Pagando invoice desde lnd2...")
    payload = {"payment_request": payment_request}
    r = requests.post(f"{LND2_REST}/v1/channels/transactions", json=payload, headers=MACAROON_LND2, verify=False)
    r.raise_for_status()
    data = r.json()
    log_event(f"Pago enviado desde lnd2: payment_error={data.get('payment_error')} | status=ok")
    print("✅ Pago enviado:", data.get("payment_error") or "sin error")


def call_lightpen_api(payment_hash_b64):
    print("📱 Llamando a /invoices/ de lightpen...")
    payload = {
        "payment_hash": payment_hash_b64,
        "amount_msat": 500_000,
        "description": "Recibo de prueba",
        "customer_name": "Cliente Test"
    }
    curl_payload = '{"payment_hash": "%s", "amount_msat": 500000, "description": "Recibo de prueba", "customer_name": "Cliente Test"}' % payment_hash_b64
    curl_command = (
        f"curl -X POST {API_URL}/invoices/ \\\n         -H 'Content-Type: application/json' \\\n         -H 'x-api-key: {API_KEY}' \\\n         -d \"{curl_payload}\""
    )
    print("\n🪙 Ejecutar manualmente con curl si es necesario:\n" + curl_command + "\n")
    r = requests.post(f"{API_URL}/invoices/", json=payload, headers=HEADERS)
    if r.status_code != 200:
        log_event(f"Error al llamar a /invoices/: status={r.status_code}, response={r.text}")
        print("❌ Error al llamar a /invoices/")
        print(f"Status: {r.status_code}")
        print("Response:", r.text)
        r.raise_for_status()
    data = r.json()
    log_event(f"Recibo generado exitosamente: {data}")
    print("📌 Recibo generado:", data)
    return data


def wait_for_payment_confirmation(payment_hash_b64, max_attempts=10):
    for attempt in range(max_attempts):
        print(f"🔁 Intentando registrar pago ({attempt+1}/{max_attempts})...")
        try:
            data = call_lightpen_api(payment_hash_b64)
            print("✅ Recibo generado con éxito")
            return data
        except requests.HTTPError as e:
            if e.response.status_code == 400 and "Pago no confirmado" in e.response.text:
                print("  ↪️ Lightpen todavía no lo reconoce como settled. Esperando...")
                log_event(f"Intento {attempt+1}: Pago aún no reconocido por Lightpen")
                time.sleep(min(5, 0.5 * 2**attempt))
                continue
            log_event(f"Error HTTP inesperado en call_lightpen_api: {e}")
            raise
    log_event("Lightpen no reconoció el pago a tiempo")
    print("❌ El pago no fue reconocido por Lightpen a tiempo.")
    exit(1)


def download_receipt(receipt_url):
    print(f"🗅️ Descargando PDF desde: {receipt_url}")
    if os.path.isfile(receipt_url):
        with open(receipt_url, "rb") as fsrc:
            with open("recibo_test.pdf", "wb") as fdst:
                fdst.write(fsrc.read())
        print("✅ Recibo copiado como recibo_test.pdf")
        log_event(f"Recibo copiado localmente desde ruta directa: {receipt_url}")
    else:
        r = requests.get(receipt_url, headers=HEADERS)
        if r.status_code == 200:
            with open("recibo_test.pdf", "wb") as f:
                f.write(r.content)
            print("✅ Recibo guardado como recibo_test.pdf")
            log_event(f"Recibo descargado exitosamente desde {receipt_url}")
        else:
            print("⚠️ No se pudo descargar el recibo:", r.status_code)
            log_event(f"Fallo al descargar recibo desde {receipt_url} | status={r.status_code}")


if __name__ == "__main__":
    wait_for_lightpen()

    run_docker_command(["docker", "exec", "lnd1", "lncli", "--network=regtest", "listinvoices"])
    run_docker_command(["docker", "exec", "lnd1", "lncli", "--network=regtest", "listchannels"])
    run_docker_command(["docker", "exec", "lnd2", "lncli", "--network=regtest", "listchannels"])

    r_hash_raw, payment_request = create_invoice_lnd1()

    if isinstance(r_hash_raw, str):
        payment_hash_hex = base64.b64decode(r_hash_raw).hex()
        payment_hash_b64 = r_hash_raw
    else:
        payment_hash_hex = r_hash_raw.hex()
        payment_hash_b64 = base64.b64encode(r_hash_raw).decode()

    print("🧐 Enviando payment_hash a Lightpen:", payment_hash_hex)
    print("🔍 Consultando estado con payment_hash (base64):", payment_hash_b64)
    log_event(f"Valores de payment_hash - HEX: {payment_hash_hex} | B64: {payment_hash_b64}")

    pay_invoice_lnd2(payment_request)

    for i in range(10):
        if is_invoice_settled(payment_hash_hex):
            print(f"✅ Invoice settled en intento {i+1}")
            log_event(f"Invoice settled detectado en intento {i+1}")
            break
        time.sleep(2)
    else:
        log_event("Invoice no settled en LND1 tras múltiples intentos")
        print("❌ El pago no fue settled en LND1 a tiempo.")
        exit(1)

    print("🕒 Esperando propagación de pago a Lightpen...")
    time.sleep(2)

    print("⏳ Esperando que el pago sea reconocido por lightpen...")
    data = wait_for_payment_confirmation(payment_hash_b64, max_attempts=10)

    if data.get("receipt_url"):
        download_receipt(data["receipt_url"])
        log_event(f"Recibo final registrado y descargado: {data['receipt_url']}")
