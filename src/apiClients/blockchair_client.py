import requests
from typing import List, Dict, Tuple
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
        """Obtiene info básica de una dirección (saldo, nº txs, etc)."""
        try:
            url = f"{self.base_url}/dashboards/address/{address}"
            params = {"key": self.api_key}
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Datos básicos obtenidos para {address}")
            logger.debug(f"Datos obtenidos para {address}: {data}")
            return data.get('data', {}).get(address, {})
        except Exception as e:
            logger.error(f"Error obteniendo datos básicos de {address}: {e}")
            return {}
        
    def get_transactions(self, address: str, start_block: int, offset: int = 0, limit: int = 100) -> List[Dict]:
        """Obtiene txs de una dirección desde un bloque (con paginación)."""
        try:
            logger.info(f"Obteniendo txs para {address} desde bloque {start_block} (offset: {offset}, limit: {limit})")
            url = f"{self.base_url}/dashboards/address/{address}"
            params = {
                "key": self.api_key,
                "limit": limit,
                "offset": offset,
                "transaction_details": "true"
            }
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if data.get('data'):
                addr_data = data.get('data', {}).get(address)
                txs = addr_data.get('transactions', [])
                logger.debug(f"Transacciones para {address} ({len(txs)}): {txs}")
                filtered_txs = []
                for tx_summary in txs:               
                    logger.info(f"Comprobando bloque de la transacción {tx_summary.get('hash')}: bloque {tx_summary.get('block_id')}")
                    logger.debug(f"Transacción (sin filtros) -> {tx_summary}")
                    block_id = tx_summary.get('block_id', 0)
                    if block_id >= start_block:
                        tx_detail = self.get_transaction_detail(tx_summary.get('hash'))
                        logger.info(f"Transacción {tx_summary.get('hash')} en bloque {block_id} la añadimos a la lista filtrada")
                        logger.debug(f"Detalles de transacción para {tx_summary.get('hash')}: {tx_detail}")
                        if tx_detail:
                            tx_summary['details'] = tx_detail
                            filtered_txs.append(tx_summary)
                    else:
                        # Las txs vienen ordenadas de más reciente a más antigua
                        # Si encontramos una anterior al start_block, ya no hay más que revisar
                        logger.info(f"Tx {tx_summary.get('hash')} es anterior al bloque {start_block}, paramos")
                        break
                logger.info(f"Seleccionadas {len(filtered_txs)} transacciones filtradas desde bloque {start_block}")
                return filtered_txs
            logger.warning(f"No hay datos para la dirección {address}")
            return []
        except Exception as e:
            logger.error(f"Error obteniendo transacciones de {address}: {e}")
            return []

    def get_all_transactions(self, address: str, start_block: int, max_records: int = 1000) ->  Tuple[List[Dict], bool]:
        """Obtiene todas las txs desde start_block paginando (máx max_records)."""
        all_txs = []
        offset = 0
        limit = 100
        logger.info(f"Obteniendo todas las txs para {address} desde bloque {start_block} (máx {max_records})")
        while offset < max_records:
            txs = self.get_transactions(address, start_block, offset=offset, limit=min(limit, max_records))
            if not txs:
                break
            all_txs.extend(txs)
            if len(txs) < limit:
                break
            offset += limit
        all_txs.sort(key=lambda tx: tx.get('block_id', 0))
        return all_txs, len(all_txs) == max_records

    def get_transaction_detail(self, txid: str) -> Dict:
        """Obtiene inputs/outputs de una tx (con cache)."""
        if txid in self.cache:
            logger.info(f"Detalles de {txid} en cache")
            return self.cache[txid]

        try:
            logger.info(f"Pidiendo detalles de {txid} a la API")
            url = f"{self.base_url}/dashboards/transactions/{txid}"
            params = {
                "key": self.api_key
            }
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if data.get('data') and txid in data['data']:
                tx_data = data['data'][txid]
                
                # Normalizamos los nombres de campos para hacerlos más claros
                inputs = tx_data.get('inputs', [])
                for inp in inputs:
                    inp['previous_txid'] = inp.get('transaction_hash')
                    inp['previous_output_index'] = inp.get('index')
                
                tx_detail = {
                    'hash': txid,
                    'time': tx_data.get('transaction', {}).get('time'),
                    'inputs': inputs,
                    'outputs': tx_data.get('outputs', []),      
                    'fee': tx_data.get('transaction', {}).get('fee', 0)
                }                       
                logger.debug(f"Detalles de tx {txid}: {tx_detail}")

                self.cache[txid] = tx_detail
                return tx_detail

            logger.warning(f"Sin datos para tx {txid}")
            return None

        except Exception as e:
            logger.error(f"Error obteniendo detalles de {txid}: {e}")
            return None
