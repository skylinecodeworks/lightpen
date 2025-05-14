import os
import requests

def get_lnd_rest_config():
    host = os.getenv("LND_REST_HOST", "127.0.0.1:8080")
    tls_cert = os.getenv("LND_TLS_CERT_PATH", "/path/to/tls.cert")
    macaroon_path = os.getenv("LND_MACAROON_PATH", "/path/to/admin.macaroon")

    if not os.path.isfile(macaroon_path):
        raise RuntimeError(f"Macaroon no encontrado en {macaroon_path}")
    with open(macaroon_path, "rb") as f:
        macaroon = f.read().hex()

    headers = {
        "Grpc-Metadata-macaroon": macaroon,
        "Content-Type": "application/json",
    }
    return host, tls_cert, headers

def check_payment(payment_hash: str) -> bool:
    """
    Consulta real al nodo LND vía REST v2 si la invoice con este payment_hash
    ha sido pagada (settled=true).
    """
    host, tls_cert, headers = get_lnd_rest_config()
    url = f"https://{host}/v2/invoices/{payment_hash}"
    try:
        resp = requests.get(url, headers=headers, verify=tls_cert)
        resp.raise_for_status()
        invoice = resp.json()
        # En v2 la respuesta es directamente el objeto Invoice:
        return invoice.get("settled", False)
    except requests.RequestException as e:
        print(f"[LND-REST] Error al consultar invoice: {e}")
        return False
