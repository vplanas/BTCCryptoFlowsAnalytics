import os
import logging
from dotenv import load_dotenv

load_dotenv()  # carga las variables de entorno desde .env

BLOCKCHAIR_API_KEY = os.getenv('BLOCKCHAIR_API_KEY')
if not BLOCKCHAIR_API_KEY:
    raise ValueError("Falta la clave API de Blockchair en el archivo .env")
BLOCKCYPHER_API_KEY = os.getenv('BLOCKCYPHER_API_KEY')
if not BLOCKCYPHER_API_KEY:
    raise ValueError("Falta la clave API de Blockcypher en el archivo .env")

THRESHOLD = 0.05  # umbral en BTC para seguir un flujo
MAX_HOPS = 9


LOG_LEVELS = {
    'src.apiClients.blockchair_client': logging.INFO,
    'src.apiClients.blockcypher_client': logging.INFO,
    'src.apiClients.walletexplorer_client': logging.INFO,
    'src.cluster_heuristics.cluster_heuristics': logging.INFO,
    'src.tracer.tracer': logging.INFO,
    'main': logging.INFO,
}

STOP_TRACE_ACTIONS_BY_WALLET_CLASSIFICATION = [
    'exchange',
    'mining',
    'mixer',
    'gambling',
    'darknet',
]