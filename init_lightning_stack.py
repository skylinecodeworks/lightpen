import os
import time
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

# === Cargar configuración desde .env
print("\U0001F527 Cargando variables desde .env...")
load_dotenv()

BITCOIN_RPC_USER = os.getenv("BITCOIN_RPC_USER", "bitcoin")
BITCOIN_RPC_PASSWORD = os.getenv("BITCOIN_RPC_PASSWORD", "bitcoin")
BITCOIN_CONTAINER = os.getenv("BITCOIN_CONTAINER", "bitcoind")
WALLET_NAME = os.getenv("BITCOIN_WALLET_NAME", "testwallet")
BITCOIN_CLI_BASE = f"docker exec {BITCOIN_CONTAINER} bitcoin-cli -regtest -rpcuser={BITCOIN_RPC_USER} -rpcpassword={BITCOIN_RPC_PASSWORD}"
BITCOIN_CLI = f"{BITCOIN_CLI_BASE} -rpcwallet={WALLET_NAME}"

LND_REST_HOST = os.getenv("LND_REST_HOST", "localhost:8080")
TLS_CERT = os.getenv("LND_TLS_CERT_PATH")
MACAROON_PATH = os.getenv("LND_MACAROON_PATH")
BASE_URL = f"https://{LND_REST_HOST}"

print(f"\U0001F50E LND_REST_HOST={LND_REST_HOST}")
print(f"\U0001F50E TLS_CERT={TLS_CERT}")
print(f"\U0001F50E MACAROON_PATH={MACAROON_PATH}")

SYNC_TIMEOUT = int(os.getenv("SYNC_TIMEOUT", 120))


def run(cmd):
    print(f"\U0001F680 Ejecutando: {cmd}")
    return subprocess.check_output(cmd, shell=True).decode().strip()

def load_macaroon_hex(path: str) -> str:
    if not Path(path).exists():
        raise FileNotFoundError(f"❌ Macaroon no encontrado: {path}")
    with open(path, "rb") as f:
        return f.read().hex()

MACAROON_HEADER = {"Grpc-Metadata-macaroon": load_macaroon_hex(MACAROON_PATH)}

# === BITCOIND ===

def bitcoind_available():
    try:
        run(f"{BITCOIN_CLI_BASE} getblockchaininfo")
        return True
    except Exception as e:
        print(f"❌ Error al acceder a bitcoind: {e}")
        return False

def ensure_wallet_loaded():
    print("\U0001F50E Verificando wallet en bitcoind...")
    wallets = run(f"{BITCOIN_CLI_BASE} listwallets")
    if WALLET_NAME in wallets:
        print(f"\U0001F4BC Wallet '{WALLET_NAME}' ya está cargado.")
        return
    print(f"🧰 Creando wallet '{WALLET_NAME}'...")
    run(f"{BITCOIN_CLI_BASE} createwallet {WALLET_NAME}")
    print("✅ Wallet creado y cargado.")

def get_block_count():
    return int(run(f"{BITCOIN_CLI} getblockcount"))

def mine_blocks_if_needed(target_blocks=101):
    current = get_block_count()
    if current >= target_blocks:
        print(f"🟢 Bitcoin ya tiene {current} bloques")
        return
    print(f"⛏️ Minando {target_blocks - current} bloques...")
    address = run(f"{BITCOIN_CLI} getnewaddress")
    run(f"{BITCOIN_CLI} generatetoaddress {target_blocks - current} {address}")
    print("✅ Minería completa")

# === LND ===

def check_lnd_ready():
    try:
        r = requests.get(f"{BASE_URL}/v1/getinfo", verify=TLS_CERT, headers=MACAROON_HEADER)
        return r.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al conectar con lnd1: {e}")
    return False

def check_wallet_locked():
    try:
        r = requests.get(f"{BASE_URL}/v1/wallet/seed", verify=TLS_CERT)
        return r.status_code == 403
    except:
        return False

def unlock_wallet():
    print("🔓 Desbloqueando wallet...")
    payload = {"wallet_password": "cGFzc3dvcmQ="}  # "password"
    r = requests.post(f"{BASE_URL}/v1/unlockwallet", json=payload, verify=TLS_CERT)
    r.raise_for_status()
    print("✅ Wallet desbloqueado")

def wait_for_lnd_sync(rest_host, tls_cert_path, macaroon_path, timeout):
    print(f"⏳ Esperando que {rest_host} se sincronice con la cadena...")
    headers = {"Grpc-Metadata-macaroon": load_macaroon_hex(macaroon_path)}
    for _ in range(timeout):
        try:
            r = requests.get(f"https://{rest_host}/v1/getinfo", headers=headers, verify=tls_cert_path)
            if r.status_code == 200:
                info = r.json()
                print(f"📊 getinfo: {info}")
                if info.get("synced_to_chain"):
                    print("✅ Nodo sincronizado con la cadena")
                    return True
        except requests.RequestException:
            pass
        time.sleep(1)
    print(f"❌ Timeout: {rest_host} no se sincronizó con la cadena en {timeout} segundos.")
    return False

def fund_lnd_node(rest_host, tls_cert_path, macaroon_path, amount_btc=1):
    print(f"💸 Fondeando nodo en {rest_host} con {amount_btc} BTC...")
    headers = {"Grpc-Metadata-macaroon": load_macaroon_hex(macaroon_path)}
    try:
        r = requests.get(f"https://{rest_host}/v1/newaddress?type=0", headers=headers, verify=tls_cert_path)
        r.raise_for_status()
        address = r.json()["address"]
        print(f"🏦 Enviando {amount_btc} BTC a {address}")
        run(f"{BITCOIN_CLI} sendtoaddress {address} {amount_btc}")
        mine_blocks_if_needed(get_block_count() + 6)
        print("✅ Fondeo y confirmación completa")
    except Exception as e:
        print(f"⚠️ No se pudo fondear {rest_host}: {e}")

# === MAIN ===

if __name__ == "__main__":
    print("\U0001F50D Esperando que bitcoind esté accesible...")
    for _ in range(10):
        if bitcoind_available():
            break
        time.sleep(2)
    else:
        print("❌ No se pudo conectar a bitcoind")
        exit(1)

    ensure_wallet_loaded()
    mine_blocks_if_needed(101)

    print("\U0001F50D Verificando estado de lnd1...")
    for _ in range(10):
        if Path(TLS_CERT).exists() and Path(MACAROON_PATH).exists():
            break
        print("⏳ Esperando archivos TLS/Macaroon...")
        time.sleep(2)
    else:
        print("❌ No se encontraron archivos TLS o macaroon.")
        exit(1)

    for _ in range(10):
        if check_lnd_ready():
            print("🟢 lnd1 ya está desbloqueado y listo.")
            fund_lnd_node(LND_REST_HOST, TLS_CERT, MACAROON_PATH)
            break
        elif check_wallet_locked():
            print("🔐 Wallet bloqueado. Intentando desbloquear...")
            try:
                unlock_wallet()
                fund_lnd_node(LND_REST_HOST, TLS_CERT, MACAROON_PATH)
                break
            except Exception as e:
                print(f"❌ Error al desbloquear wallet: {e}")
                exit(1)
        else:
            print("📅 El nodo no responde como bloqueado ni inicializado. Verificá manualmente.")
            exit(1)

    LND2_REST = os.getenv("LND2_REST_HOST")
    LND2_CERT = os.getenv("LND2_TLS_CERT_PATH")
    LND2_MACAROON = os.getenv("LND2_MACAROON_PATH")

    print(f"\U0001F50E LND2_REST_HOST={LND2_REST}")
    print(f"\U0001F50E LND2_TLS_CERT_PATH={LND2_CERT}")
    print(f"\U0001F50E LND2_MACAROON_PATH={LND2_MACAROON}")

    if LND2_REST and Path(LND2_CERT).exists() and Path(LND2_MACAROON).exists():
        fund_lnd_node(LND2_REST, LND2_CERT, LND2_MACAROON)
        try:
            info = requests.get(f"https://{LND_REST_HOST}/v1/getinfo", headers=MACAROON_HEADER, verify=TLS_CERT).json()
            pubkey = info["identity_pubkey"]
            if wait_for_lnd_sync(LND2_REST, LND2_CERT, LND2_MACAROON, SYNC_TIMEOUT):
                print("✅ LND2 sincronizado y listo para conexión y canal (continuar lógica aquí)")
            else:
                print("⚠️ Saltando conexión y apertura de canal: lnd2 no está sincronizado")
        except Exception as e:
            print(f"⚠️ No se pudo obtener información de lnd1 para abrir canal: {e}")
    else:
        print("ℹ️ Saltando fondeo de lnd2: configuración incompleta")
