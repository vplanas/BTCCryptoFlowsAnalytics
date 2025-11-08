import sys
import logging
from src.utils.logger import get_logger
from src.apiClients.blockchair_client import BlockchairClient
from src.apiClients.walletexplorer_client import WalletExplorerClient

logger = get_logger(__name__)

def main():
    if len(sys.argv) == 2:
        root_address = sys.argv[1]
    else:
        root_address = "15JFh88FcE4WL6qeMLgX5VEAFCbRXjc9fr"  # ejemplo dirección para test

    logger.info(f"Analizando dirección raíz: {root_address}")

    blockchair_client = BlockchairClient()
    wallet_explorer_client = WalletExplorerClient()

    # Obtener datos básicos con Blockchair
    basic_info = blockchair_client.get_address_info(root_address)
    if not basic_info:
        logger.warning(f"No se pudo obtener información básica para {root_address}")
        return

    # Extraer y mostrar datos clave
    balance = basic_info.get('address', {}).get('balance', 'Desconocido')
    tx_count = basic_info.get('address', {}).get('transaction_count', 'Desconocido')
    last_activity = basic_info.get('address', {}).get('last_activity', 'Desconocido')
    logger.info(f"Dirección: {root_address}")
    logger.info(f"Balance: {balance}")
    logger.info(f"Número de transacciones: {tx_count}")
    logger.info(f"Última actividad: {last_activity}")

    # Buscar wallet ID en Wallet Explorer para la dirección
    wallet_id = wallet_explorer_client.get_wallet_id_from_address(root_address)
    if wallet_id:
        logger.info(f"Wallet Explorer identificó el wallet: {wallet_id}")
        # Obtener transacciones del wallet en Wallet Explorer
        wallet_txs = wallet_explorer_client.get_wallet_transactions(wallet_id)
        logger.info(f"Transacciones obtenidas de Wallet Explorer: {len(wallet_txs.get('transactions', []))}")
    else:
        logger.warning(f"No se encontró wallet asociado en Wallet Explorer para {root_address}")

    # Obtener transacciones detalladas de Blockchair para la dirección
    transactions = blockchair_client.get_transactions(root_address, limit=50)
    logger.info(f"Transacciones detalladas desde Blockchair: {len(transactions)}")
if __name__ == "__main__":
    main()