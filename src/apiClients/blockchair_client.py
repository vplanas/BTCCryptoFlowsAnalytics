import requests
import time
from typing import List, Dict
from src.utils.logger import get_logger
from config import BLOCKCHAIR_API_KEY

logger = get_logger(__name__)

class BlockchairClient:
    def __init__(self, api_key: str = BLOCKCHAIR_API_KEY, timeout: float = 10.0):
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = "https://api.blockchair.com/bitcoin"
        self.cache = {}

    def get_address_info(self, address: str) -> Dict:
        """
        Obtiene datos básicos de la dirección: saldo, número de transacciones, etc.
        """
        try:
            url = f"{self.base_url}/dashboards/address/{address}"
            params = {"key": self.api_key}
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Datos básicos obtenidos para {address}")
            return data.get('data', {}).get(address, {})
        except Exception as e:
            logger.error(f"Error obteniendo datos básicos de {address}: {e}")
            return {}

    def get_transactions(self, address: str, limit: int = 100) -> List[Dict]:
        """
        Obtiene todas las transacciones de una dirección.
        Primer paso: obtener lista de txids desde /dashboards/address
        Segundo paso: para cada txid, obtener detalles desde /dashboards/transactions
        """
        try:
            url = f"{self.base_url}/dashboards/address/{address}"
            params = {
                "transaction_details": "true",
                "limit": f"{limit},0",
                "key": self.api_key
            }
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if data.get('data') and address in data['data']:
                addr_data = data['data'][address]
                transactions = addr_data.get('transactions', [])

                logger.info(f"Encontradas {len(transactions)} transacciones para {address}")
                txs_detailed = []
                for tx_summary in transactions:
                    txid = tx_summary['hash']
                    logger.debug(f"Obteniendo detalles de {txid}")
                    tx_detail = self.get_transaction_detail(txid)
                    if tx_detail:
                        txs_detailed.append(tx_detail)
                    time.sleep(0.1)  # Evitar rate limit

                return txs_detailed

            logger.warning(f"Sin datos para {address}")
            return []

        except Exception as e:
            logger.error(f"Error obteniendo transacciones de {address}: {e}")
            return []

    def get_transaction_detail(self, txid: str) -> Dict:
        """
        Obtiene detalles completos de una transacción (inputs y outputs).
        """
        if txid in self.cache:
            logger.debug(f"Usando cache para tx {txid}")
            return self.cache[txid]

        try:
            url = f"{self.base_url}/dashboards/transactions/{txid}"
            params = {"key": self.api_key}
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if data.get('data') and txid in data['data']:
                tx_data = data['data'][txid]
                tx_detail = {
                    'hash': txid,
                    'time': tx_data.get('transaction', {}).get('time'),
                    'inputs': tx_data.get('inputs', []),
                    'outputs': tx_data.get('outputs', [])
                }
                logger.info(f"Detalles obtenidos para tx {txid}")

                self.cache[txid] = tx_detail
                return tx_detail

            logger.warning(f"Sin datos para tx {txid}")
            return None

        except Exception as e:
            logger.error(f"Error obteniendo detalles de {txid}: {e}")
            return None
