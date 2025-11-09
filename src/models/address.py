from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

# Modelo para una dirección Bitcoin
@dataclass
class Address:
    """
    Representa una dirección Bitcoin individual y sus propiedades relevantes.
    """
    address: str            # Dirección Bitcoin
    balance: float          # Saldo actual en la dirección
    tx_count: int           # Número total de transacciones
    last_activity: Optional[datetime] = None   # Fecha de última actividad
    wallet_explorer_id: str = ""               # Identificador del wallet en Wallet Explorer
    wallet_classification: str = ""            # Heurística de clasificación del wallet