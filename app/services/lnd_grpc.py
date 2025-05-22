import os
from dotenv import load_dotenv
from lndgrpc import LNDClient

load_dotenv()

macaroon_filepath = os.getenv("LND_MACAROON_PATH")
cert_filepath = os.getenv("LND_TLS_CERT_PATH")
grpc_host = os.getenv("LND_GRPC_HOST")

if not all([macaroon_filepath, cert_filepath, grpc_host]):
    raise RuntimeError("Faltan variables de entorno requeridas")

class LndGrpcClient:
    def __init__(self, ip_address=None, network=None, macaroon_path=None, cert_path=None):
        self.client = LNDClient(
            ip_address=ip_address or os.getenv("LND_GRPC_HOST", "127.0.0.1:10009"),
            network=network or os.getenv("LND_NETWORK", "regtest"),
            macaroon_filepath=macaroon_path or os.getenv("LND_MACAROON_PATH"),
            cert_filepath=cert_path or os.getenv("LND_TLS_CERT_PATH"),
            admin=True
        )

    def add_invoice(self, amount_sat: int, memo: str = ""):
        response = self.client.add_invoice(value=amount_sat, memo=memo)
        return {
            "r_hash": response.r_hash.hex(),
            "payment_request": response.payment_request,
        }

    def lookup_invoice(self, r_hash_hex: str):
        invoice = self.client.lookup_invoice(r_hash_str=r_hash_hex)
        return {
            "settled": invoice.settled,
            "memo": invoice.memo,
            "amt_paid_sat": invoice.amt_paid_sat,
        }

    def check_payment(self, payment_hash_hex: str) -> bool:
        try:
            invoice = self.client.lookup_invoice(r_hash_str=payment_hash_hex)
            return invoice.settled
        except Exception as e:
            print(f"[❌] Error al verificar invoice: {e}")
            return False
