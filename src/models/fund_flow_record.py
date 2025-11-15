from dataclasses import dataclass
from datetime import datetime

'''''
El decorador @dataclass automatiza la generación de métodos comunes en las clases de Python,
como el constructor (init), el representador (repr) y el comparador (eq),
'''
@dataclass
class FundFlowRecord:
    """
    Representa un registro individual en el seguimiento del flujo de fondos en blockchain.
    Cada registro describe un 'hop' del fondo, con detalles sobre origen y destino,
    clasificación, y métricas para análisis forense.
    """

    seed_case: str              # Dirección o caso semilla del rastreo
    path_id: int               # ID del camino o ruta seguida por el flujo
    hop: int                   # Número ordenado del salto dentro del path
    follow: bool               # Indica si continuar siguiendo el flujo por este hop

    input: str                 # Dirección origen en este hop
    output: str                # Dirección destino en este hop
    wallet_explorer_id: str    # ID del wallet en Wallet Explorer asociado al output
    wallet_classification: str # Clasificación heurística del wallet output (Exchange, Mixer, etc)

    wallet_label: str           # Etiqueta categórica genérica para el destino si se puede averigurar(Darkside, FBI, Unknown, ...)
    txid: str                  # ID de transacción en blockchain que representa este movimiento
    datetime_CET: datetime     # Fecha y hora del evento ajustado a CET
    mov_type: str              # Tipo de movimiento ('OUT' o 'IN') en relación al caso
    BTC: float                 # Cantidad de bitcoins movidos en este hop
    classification: str        # Clasificación del movimiento según heurísticas o análisis personalizado

    BTC_added_to_flow_from_others: float = 0.0   # BTC añadidos al seguimiento desde otras fuentes
    BTC_not_followed: float = 0.0                 # BTC en este hop no seguidos explícitamente
    notes: str = ""                               # Comentarios o notas adicionales
