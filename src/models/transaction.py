from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class Transaction:
    """
    Representa una transacción on-chain, con detalles
    """
    txid: str                           # ID de la transacción
    block_time: Optional[datetime]      # Fecha y hora de la confirmación
    inputs: List[str]                   # Direcciones origen de la transacción
    outputs: List[str]                  # Direcciones destino de la transacción
    amount_in: float                    # BTC total en entradas
    amount_out: float                   # BTC total en salidas
    fee: float                          # Tarifa en BTC
    input_wallets: List[str] = None     # Wallets (clusters) implicados en los inputs
    output_wallets: List[str] = None    # Wallets implicados en los outputs

