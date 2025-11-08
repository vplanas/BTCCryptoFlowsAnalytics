from dataclasses import dataclass
from datetime import datetime

@dataclass
class FundFlowRecord:
    """
    Clase que representa un registro individual del seguimiento de fondos en la cadena de bloques.
    Cada instancia corresponde a un 'hop' o evento en el flujo de bitcoins, con atributos que describen
    los datos relevantes para el análisis forense del movimiento de fondos.
    """

    # Dirección o caso semilla desde donde se empieza el rastreo.
    seed_case: str

    # Identificador de la ruta o camino que sigue el flujo de fondos.
    path_id: int

    # Número de salto o paso dentro del seguimiento (orden cronológico en la ruta).
    hop: int

    # Booleano para indicar si este hop debe continuar siguiendo la ruta de fondos.
    follow: bool

    # Dirección de entrada (de donde vienen los fondos en este hop).
    input: str

    # Dirección de salida (a dónde van los fondos en este hop).
    output: str

    # Etiqueta categórica del destino, p.ej., "Darkside", "FBI", "Unknown".
    dest_tag: str

    # ID de la transacción en blockchain que representa este movimiento.
    txid: str

    # Fecha y hora del evento de movimiento, ajustado a CET.
    datetime_CET: datetime

    # Tipo de movimiento, 'OUT', 'IN'
    mov_type: str

    # Cantidad de bitcoins movidos en este hop.
    BTC: float

    # Clasificación del movimiento según heurísticas o análisis personalizado, p.ej., "Exchange", "Mixer", ...
    classification: str

    # Cantidad de BTC añadidos al flujo desde otras fuentes en este hop.
    BTC_added_to_flow_from_others: float = 0.0

    # BTC en este hop que no fueron seguidos explícitamente (perdidos o ignorados).
    BTC_not_followed: float = 0.0

    # Comentarios adicionales para notas o explicaciones.
    notes: str = ""

    def to_dict(self):
        """
        Convierte la instancia en un diccionario con campos y nombres adecuados
        para exportación a CSV o manipulación en estructuras de datos.
        """
        return {
            "seed_case": self.seed_case,
            "path_id": self.path_id,
            "hop": self.hop,
            "follow": self.follow,
            "input": self.input,
            "output": self.output,
            "dest_tag": self.dest_tag,
            "txid": self.txid,
            "datetime_CET": self.datetime_CET,
            "mov_type": self.mov_type,
            "BTC": self.BTC,
            "classification": self.classification,
            "BTC_added_to_flow_from_others": self.BTC_added_to_flow_from_others,
            "BTC_not_followed": self.BTC_not_followed,
            "notes": self.notes
        }
