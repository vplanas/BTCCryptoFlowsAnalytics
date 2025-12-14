import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Cargar las API keys desde .env
BLOCKCHAIR_API_KEY = os.getenv('BLOCKCHAIR_API_KEY')
if not BLOCKCHAIR_API_KEY:
    raise ValueError("Falta BLOCKCHAIR_API_KEY en el .env")
BLOCKCYPHER_API_KEY = os.getenv('BLOCKCYPHER_API_KEY')
if not BLOCKCYPHER_API_KEY:
    raise ValueError("Falta BLOCKCYPHER_API_KEY en el .env")

# Parámetros del rastreo
THRESHOLD = 0.05  # 5% del total recibido en la dirección inicial
MAX_HOPS = 9

# Niveles de log por módulo
LOG_LEVELS = {
    'src.apiClients.blockchair_client': logging.WARNING,
    'src.apiClients.blockcypher_client': logging.INFO,
    'src.apiClients.walletexplorer_client': logging.WARNING,
    'src.cluster_heuristics.cluster_heuristics': logging.INFO,
    'src.tracer.tracer': logging.DEBUG,
    'main': logging.INFO,
}

# Tipos de wallet donde paramos el rastreo
STOP_TRACE_ACTIONS_BY_WALLET_CLASSIFICATION = [
    'exchange',
    'mining',
    'mixer',
    'gambling',
    'darknet',
]