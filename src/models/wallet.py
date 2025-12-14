from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

# Modelo para un wallet o cluster identificado
@dataclass
class Wallet:
    """Modelo para un wallet/cluster con varias direcciones."""
    wallet_id: str          # ID/etiqueta del wallet
    addresses: List[str]    # Lista de direcciones asociadas
    label: str = ""         # Etiqueta o nombre asignado por heurística o WalletExplorer o otros
    classification: str = ""# Ej: Exchange, Mixer, Service, etc.
    tx_count: int = 0       # Número total de transacciones del cluster
    total_balance: float = 0.0 # Suma del balance de todas las direcciones