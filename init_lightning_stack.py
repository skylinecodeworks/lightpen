import os
import time
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

# === Cargar configuración desde .env
print("🔧 Cargando variables desde .env...")
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

print(f"🔎 LND_REST_HOST={LND_REST_HOST}")
print(f"🔎 TLS_CERT={TLS_CERT}")
print(f"🔎 MACAROON_PATH={MACAROON_PATH}")

def run(cmd):
    print(f"🚀 Ejecutando: {cmd}")
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
    print("🔎 Verificando wallet en bitcoind...")
    wallets = run(f"{BITCOIN_CLI_BASE} listwallets")
    if WALLET_NAME in wallets:
        print(f"💼 Wallet '{WALLET_NAME}' ya está cargado.")
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
    except requests.exceptions.SSLError:
        print("❌ Error de certificado TLS")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")
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

def fund_lnd_node(rest_host, tls_cert_path, macaroon_path, amount_btc=1):
    print(f"💸 Fondeando nodo en {rest_host} con {amount_btc} BTC...")
    if not Path(tls_cert_path).exists():
        print(f"❌ Certificado TLS no encontrado: {tls_cert_path}")
        return
    if not Path(macaroon_path).exists():
        print(f"❌ Macaroon no encontrado: {macaroon_path}")
        return

    headers = {"Grpc-Metadata-macaroon": load_macaroon_hex(macaroon_path)}
    try:
        r = requests.get(f"https://{rest_host}/v1/newaddress?type=0", headers=headers, verify=tls_cert_path)
        r.raise_for_status()
        address = r.json()["address"]
        print(f"🏦 Enviando {amount_btc} BTC a {address}")
        run(f"{BITCOIN_CLI} sendtoaddress {address} {amount_btc}")
        btc_address = run(f"{BITCOIN_CLI} getnewaddress")
        run(f"{BITCOIN_CLI} generatetoaddress 6 {btc_address}")
        print("✅ Fondeo y confirmación completa")
    except Exception as e:
        print(f"⚠️ No se pudo fondear {rest_host}: {e}")

def connect_peers(lnd2_rest, lnd2_cert, lnd2_macaroon, pubkey, host):
    print(f"🔌 Conectando lnd2 con {pubkey}@{host}...")
    headers = {"Grpc-Metadata-macaroon": load_macaroon_hex(lnd2_macaroon)}
    payload = {"addr": {"pubkey": pubkey, "host": host}, "perm": True}
    try:
        r = requests.post(f"https://{lnd2_rest}/v1/peers", json=payload, headers=headers, verify=lnd2_cert)
        if r.status_code == 409:
            print("⚠️ Ya estaban conectados.")
        else:
            r.raise_for_status()
            print("✅ Conexión establecida")
    except Exception as e:
        print(f"⚠️ Error al conectar nodos: {e}")

def open_channel(lnd2_rest, lnd2_cert, lnd2_macaroon, pubkey, host, amount_sat=1000000):
    print(f"🔗 Abriendo canal desde lnd2 hacia {pubkey}@{host} con {amount_sat} sat...")
    headers = {"Grpc-Metadata-macaroon": load_macaroon_hex(lnd2_macaroon)}
    payload = {"node_pubkey_string": pubkey, "local_funding_amount": amount_sat}
    try:
        r = requests.post(f"https://{lnd2_rest}/v1/channels", json=payload, headers=headers, verify=lnd2_cert)
        r.raise_for_status()
        print("✅ Canal abierto correctamente")
        btc_address = run(f"{BITCOIN_CLI} getnewaddress")
        run(f"{BITCOIN_CLI} generatetoaddress 6 {btc_address}")
        print("⛏️ Canal minado y confirmado")
    except Exception as e:
        print(f"⚠️ Error al abrir canal: {e}")

# === MAIN ===

if __name__ == "__main__":
    print("🔍 Esperando que bitcoind esté accesible...")
    for _ in range(10):
        if bitcoind_available():
            break
        time.sleep(2)
    else:
        print("❌ No se pudo conectar a bitcoind")
        exit(1)

    ensure_wallet_loaded()
    mine_blocks_if_needed(101)

    print("🔍 Verificando estado de lnd1...")
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
                print("✅ Wallet desbloqueado")
                fund_lnd_node(LND_REST_HOST, TLS_CERT, MACAROON_PATH)
                break
            except Exception as e:
                print(f"❌ Error al desbloquear wallet: {e}")
                exit(1)
        else:
            print("📅 El nodo no responde como bloqueado ni inicializado. Verificá manualmente con curl o reiniciá el entorno.")
            exit(1)

    # Fondear lnd2 automáticamente si está configurado
    LND2_REST = os.getenv("LND2_REST_HOST")
    LND2_CERT = os.getenv("LND2_TLS_CERT_PATH")
    LND2_MACAROON = os.getenv("LND2_MACAROON_PATH")

    print(f"🔍 LND2_REST_HOST={LND2_REST}")
    print(f"🔍 LND2_TLS_CERT_PATH={LND2_CERT}")
    print(f"🔍 LND2_MACAROON_PATH={LND2_MACAROON}")

    if LND2_REST and Path(LND2_CERT).exists() and Path(LND2_MACAROON).exists():
        fund_lnd_node(LND2_REST, LND2_CERT, LND2_MACAROON)
        try:
            info = requests.get(f"https://{LND_REST_HOST}/v1/getinfo", headers=MACAROON_HEADER, verify=TLS_CERT).json()
            pubkey = info["identity_pubkey"]
            connect_peers(LND2_REST, LND2_CERT, LND2_MACAROON, pubkey, "lnd1:9735")
            open_channel(LND2_REST, LND2_CERT, LND2_MACAROON, pubkey, "lnd1:9735")
        except Exception as e:
            print(f"⚠️ No se pudo obtener información de lnd1 para abrir canal: {e}")
    else:
        print("ℹ️ Saltando fondeo de lnd2: configuración incompleta")
