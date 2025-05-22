import os
import time
import json
import subprocess
import requests
from app.services.lnd_grpc import LndGrpcClient

API_URL = "http://localhost:8000/invoices"
API_KEY = os.getenv("API_KEY", "test-key-123")


def run(*args):
    return subprocess.run(args, capture_output=True, text=True)

def get_lnd2_new_address():
    result = run("docker", "exec", "lnd2", "lncli", "--network=regtest", "--rpcserver=localhost:10010", "newaddress", "p2wkh")
    return json.loads(result.stdout)["address"]

def send_to_address(address):
    return run("docker", "exec", "bitcoind", "bitcoin-cli", "-regtest", "-rpcuser=bitcoin", "-rpcpassword=bitcoin", "sendtoaddress", address, "1.0")

def mine_blocks(n=6):
    addr = run("docker", "exec", "bitcoind", "bitcoin-cli", "-regtest", "-rpcuser=bitcoin", "-rpcpassword=bitcoin", "getnewaddress").stdout.strip()
    run("docker", "exec", "bitcoind", "bitcoin-cli", "-regtest", "-rpcuser=bitcoin", "-rpcpassword=bitcoin", "generatetoaddress", str(n), addr)

def check_wallet_balance():
    result = run("docker", "exec", "lnd2", "lncli", "--network=regtest", "--rpcserver=localhost:10010", "walletbalance")
    data = json.loads(result.stdout)
    return int(data["confirmed_balance"])

def connect_peers(pubkey):
    run("docker", "exec", "lnd2", "lncli", "--network=regtest", "--rpcserver=localhost:10010", "connect", f"{pubkey}@lnd1:9735")

def open_channel(pubkey):
    return run("docker", "exec", "lnd2", "lncli", "--network=regtest", "--rpcserver=localhost:10010", "openchannel", "--node_key="+pubkey, "--local_amt=1000000")

def list_channels():
    result = run("docker", "exec", "lnd2", "lncli", "--network=regtest", "--rpcserver=localhost:10010", "listchannels")
    return json.loads(result.stdout)["channels"]

if __name__ == "__main__":
    print("📡 Obteniendo pubkey de LND1...")
    pubkey = json.loads(run("docker", "exec", "lnd1", "lncli", "--network=regtest", "getinfo").stdout)["identity_pubkey"]

    print("🔗 Conectando LND2 a LND1...")
    connect_peers(pubkey)

    if check_wallet_balance() < 1000000:
        print("💸 Fondeando LND2...")
        address = get_lnd2_new_address()
        send_to_address(address)
        mine_blocks(6)
        time.sleep(2)

    if not list_channels():
        print("🪟 Abriendo canal...")
        open_channel(pubkey)
        mine_blocks(6)
        time.sleep(2)

    # Crear invoice y pagarla
    lnd1 = LndGrpcClient()
    lnd2 = LndGrpcClient(
        ip_address="localhost:10010",
        macaroon_path="./docker/lnd/lnd2-data/data/chain/bitcoin/regtest/admin.macaroon",
        cert_path="./docker/lnd/lnd2-data/tls.cert"
    )

    print("🚀 Creando invoice gRPC por 500 sats...")
    invoice = lnd1.add_invoice(amount_sat=500, memo="Prueba vía gRPC")
    print(f"📦 payment_request: {invoice['payment_request']}")
    print(f"🔑 r_hash: {invoice['r_hash']}")

    print("⚡️ LND2 intentando pagar la invoice...")
    payment = lnd2.client.send_payment(invoice['payment_request'])
    print(f"💸 Estado del pago: {payment.payment_error or 'OK'}")

    print("⏳ Esperando que la invoice sea pagada...")
    for attempt in range(10):
        invoice_status = lnd1.lookup_invoice(invoice["r_hash"])
        print(f"🔍 Intento {attempt + 1}: settled={invoice_status['settled']}")
        if invoice_status["settled"]:
            print("✅ Invoice pagada.")
            break
        time.sleep(2)
    else:
        print("❌ La invoice no fue pagada a tiempo.")
        exit(1)

    # ⬇️ Enviar la invoice al backend y verificar recibo
    print("📨 Enviando invoice al backend para generar recibo...")
    payload = {
        "payment_hash": invoice["r_hash"],
        "amount_msat": 500 * 1000,
        "description": "Prueba vía gRPC",
        "customer_name": "Test User"
    }
    headers = {"x-api-key": API_KEY}

    response = requests.post(API_URL, json=payload, headers=headers)
    if response.status_code != 200:
        print(f"❌ Error en la creación del recibo: {response.status_code} {response.text}")
        exit(1)

    data = response.json()
    print("📄 Recibo generado:")
    print(f"🧾 invoice_id: {data['invoice_id']}")
    print(f"📎 receipt_id: {data['receipt_id']}")
    print(f"🔗 receipt_url: {data['receipt_url']}")
    print(f"🖋 ALL: {data}")