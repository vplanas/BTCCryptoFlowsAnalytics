import requests
from src.utils.logger import get_logger

logger = get_logger(__name__)

class WalletExplorerClient:

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.base_url = "https://www.walletexplorer.com/api/1"

    def get_wallet_id_from_address(self, address: str):
        """
        Consulta la API para obtener wallet ID desde una dirección dada.
        """
        url = f"{self.base_url}/address-lookup"
        params = {"address": address}
        try:
            logger.debug(f"Buscando wallet para dirección: {address}")
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            logger.debug(f"Respuesta address-lookup: {data}")
            if data.get('found'):
                return data.get('wallet_id')
            return None
        except requests.RequestException as e:
            logger.error(f"Error en address-lookup: {e}")
            raise

    def get_wallet_transactions(self, wallet_id: str, from_idx: int = 0, count: int = 100):
        """
        Obtiene transacciones de un wallet dado el wallet ID.
        """
        url = f"{self.base_url}/wallet"
        params = {
            "wallet": wallet_id,
            "from": from_idx,
            "count": count
        }
        try:
            logger.debug(f"Consultando transacciones para wallet: {wallet_id}")
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            logger.debug(f"Respuesta wallet transactions: {data}")
            return data
        except requests.RequestException as e:
            logger.error(f"Error en wallet transactions: {e}")
            raise
