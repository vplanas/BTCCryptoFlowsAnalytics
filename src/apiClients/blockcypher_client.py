import requests
from typing import List, Dict
from src.utils.logger import get_logger
from config import BLOCKCYPHER_API_KEY
import time


logger = get_logger(__name__)


# Cliente para la API de BlockCypher
class BlockCypherClient:
    def __init__(self, apikey: str = BLOCKCYPHER_API_KEY, timeout: float = 10.0):
        self.apikey = apikey
        self.timeout = timeout
        self.baseurl = "https://api.blockcypher.com/v1/btc/main"
        self.cache = {}
        self.last_call_time = 0
        logger.debug(f"BlockCypherClient inicializado con timeout={timeout}s")


    # Espera para respetar el rate limit de la API
    def _wait_for_rate_limit(self):
        """Espera 0.34s entre calls para <3/seg."""
        current_time = time.time()
        time_since_last = current_time - self.last_call_time
        if time_since_last < 0.34:
            sleep_time = 0.34 - time_since_last
            logger.debug(f"Rate limit: esperando {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self.last_call_time = time.time()


    # Obtener transacciones posteriores entre dos bloques específicos, si la direccion tiene muchas transacciones puede devolver "nada", antes de llamar a este metodo se deberia comprobar el numero de transacciones de la direccion
    def get_txs_between_blocks(self, address: str, after: int, before: int) -> List[Dict]:
        """Obtiene hasta 50 txs > block_height."""
        logger.info(f"Solicitando txs para {address} entre bloques {after} y {before}")
        self._wait_for_rate_limit()
        
        cache_key = f"{address}_{after}_{before}_txs"
        if cache_key in self.cache:
            logger.debug(f"Txs para {address} (bloques {after}-{before}) desde cache")
            return self.cache[cache_key]

        url = f"{self.baseurl}/addrs/{address}/full"
        params = {
            'after': after,
            'before': before,
            'limit': 50,
            'token': self.apikey
        }
        
        logger.debug(f"Llamando a BlockCypher: {url}")
        
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            txs = data.get('txs', [])
            self.cache[cache_key] = txs
            
            if txs:
                logger.info(f"Obtenidas {len(txs)} txs para {address} en block> {after} y < {before}.")
            else:
                logger.warning(f"No se obtuvieron txs para {address} entre bloques {after}-{before}")
            
            return txs
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                logger.error(f"Rate limit excedido para {address}. Reintenta más tarde.")
            else:
                logger.error(f"Error HTTP {response.status_code} para {address}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error obteniendo txs: {e}")
            return []
