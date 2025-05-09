import os
import random

def check_payment(payment_hash: str) -> bool:
    """
    Simula la verificación del estado de pago en LND.
    En versión real, consultará el endpoint REST de LND.
    """
    # Simulación por ahora
    print(f"[LND] Verificando estado de pago para hash: {payment_hash}")
    # Simula aleatoriamente que algunos están pagos
    return random.choice([True, True, False])
