import requests
from typing import List, Tuple, Dict, Union, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)

class WalletExplorerClient:

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.base_url = "https://www.walletexplorer.com/api/1"

    def get_wallet_from_address(self, address: str) -> Optional[Dict]:
        """
        Consulta la API para obtener wallet info desde una dirección.
        Retorna el objeto completo de la API si found=True, o None si no encontrado.
        
        Ejemplo de respuesta:
        {
            "found": true,
            "label": "Kraken.com",
            "wallet_id": "00001012b1848923",
            "updated_to_block": 923639
        }
        """
        url = f"{self.base_url}/address-lookup"
        params = {"address": address}
        try:
            logger.debug(f"Buscando wallet para dirección: {address}")
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if data.get('found'):
                logger.debug(f"Wallet encontrado: {data.get('wallet_id')}" + 
                           (f" (label: {data.get('label')})" if data.get('label') else ""))
                return data
            
            logger.debug(f"Dirección {address} no encontrada en ningún cluster")
            return None
            
        except requests.RequestException as e:
            logger.error(f"Error en address-lookup: {e}")
            raise

    def get_wallet_transactions(self, wallet_id: str, from_idx: int = 0, count: int = 100) -> Optional[Dict]:
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
            return data
        except requests.RequestException as e:
            logger.error(f"Error en wallet transactions: {e}")
            raise

    def get_wallet_addresses(self, wallet_id: str, from_idaddr: int = 0, count: int = 100) -> Optional[Dict]:
        """     
        Obtiene las direcciones asociadas a un wallet dado el wallet ID.
        """
        url = f"{self.base_url}/wallet-addresses"
        params = {
            "wallet": wallet_id,
            "from": from_idaddr,
            "count": count
        }
        try:
            logger.debug(f"Consultando direcciones para wallet: {wallet_id}")
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.RequestException as e:
            logger.error(f"Error en wallet addresses: {e}")
            raise
