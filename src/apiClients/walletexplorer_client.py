import requests
from src.utils.logger import get_logger

logger = get_logger(__name__)

class WalletExplorerClient:
    BASE_URL = "https://www.walletexplorer.com/api/1"

    def get_wallet_id_from_address(self, address):
        """
        Consulta la API para obtener wallet ID desde una dirección dada.
        """
        url = f"{self.BASE_URL}/address-lookup"
        params = {"address": address}
        try:
            logger.debug(f"Buscando wallet para dirección: {address}")
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            logger.debug(f"Respuesta address-lookup: {data}")
            # La respuesta incluye 'address', 'wallet' si existe, o 'found': false
            return data.get('wallet')  # Puede ser None si no encuentra wallet
        except requests.RequestException as e:
            logger.error(f"Error en address-lookup: {e}")
            raise

    def get_wallet_transactions(self, wallet_id, from_idx=0, count=100):
        """
        Obtiene transacciones de un wallet dado el wallet ID.
        """
        url = f"{self.BASE_URL}/wallet"
        params = {
            "wallet": wallet_id,
            "from": from_idx,
            "count": count
        }
        try:
            logger.debug(f"Consultando transacciones para wallet: {wallet_id}")
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            logger.debug(f"Respuesta wallet transactions: {data}")
            return data
        except requests.RequestException as e:
            logger.error(f"Error en wallet transactions: {e}")
            raise
