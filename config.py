import os
import logging
from dotenv import load_dotenv

load_dotenv()  # carga las variables de entorno desde .env

BLOCKCHAIR_API_KEY = os.getenv('BLOCKCHAIR_API_KEY')
if not BLOCKCHAIR_API_KEY:
    raise ValueError("Falta la clave API de Blockchair en el archivo .env")

THRESHOLD = 0.1
MAX_HOPS = 9


LOG_LEVELS = {
    'src.apiClients.blockchair_client': logging.INFO,
    'src.tracer.tracer': logging.DEBUG,
    'main': logging.INFO,
}