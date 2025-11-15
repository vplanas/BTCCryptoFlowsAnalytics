from typing import Dict, List, Optional
from src.utils.logger import get_logger
from src.apiClients.walletexplorer_client import WalletExplorerClient

logger = get_logger(__name__)

class ClusterHeuristics:
    """
    Clasifica clusters (wallets) de WalletExplorer mediante análisis de transacciones.
    """
    
    # Mapeo de labels de WalletExplorer a tipos de cluster
    LABEL_MAPPINGS = {
        'exchange': ['binance', 'coinbase', 'kraken', 'bitfinex', 'bitstamp', 'huobi', 'okex', 'bittrex', 'poloniex'],
        'mining': ['pool', 'f2pool', 'antpool', 'btc.com', 'slushpool', 'viaBTC', 'mining'],
        'mixer': ['wasabi', 'samourai', 'chipmixer', 'blender', 'bitcoin fog', 'CoinJoinMess'],
        'gambling': ['satoshidice', 'primedice', 'bustabit'],
        'darknet': ['silk road', 'alphabay', 'hydra']
    }
    
    def __init__(self, walletexplorer_client: WalletExplorerClient = None):
        self.client = walletexplorer_client or WalletExplorerClient()
        self.cache = {}
        logger.debug("ClusterHeuristics inicializado.")
    
    def classify_address(self, address: str) -> Dict:
        """
        Clasifica una dirección obteniendo su cluster y analizándolo.
        """
        logger.info(f"Iniciando clasificación de dirección: {address}")
        try:
            # Obtener wallet info completo
            wallet_info = self.client.get_wallet_from_address(address)
            
            if not wallet_info:
                logger.warning(f"Dirección {address} no pertenece a ningún cluster conocido.")
                return {
                    'cluster_type': 'unclustered',
                    'wallet_id': None,
                    'confidence': 0.0,
                    'description': 'Dirección no pertenece a ningún cluster conocido'
                }
            
            wallet_id = wallet_info.get('wallet_id')
            wallet_label = wallet_info.get('label') or ""
            
            logger.debug(f"Dirección {address} pertenece al cluster {wallet_id}" + 
                        (f" (label: {wallet_label})" if wallet_label else ""))
            
            # Si tiene label, clasificar directamente
            if wallet_label:
                result = self._classify_from_label(wallet_id, wallet_label)
                self.cache[wallet_id] = result
                logger.info(f"Clasificado por label en {result['cluster_type']} (confianza: {result['confidence']:.2f})")
                return result
            
            # Sin label, usar heurísticas
            return self.classify_cluster(wallet_id)
            
        except Exception as e:
            logger.error(f"Error clasificando dirección {address}: {e}")
            return self._error_result(str(e))
    
    def classify_cluster(self, wallet_id: str) -> Dict:
        """
        Clasifica un cluster usando heurísticas (cuando no tiene label).
        """
        if wallet_id in self.cache:
            logger.info(f"Clasificación de cluster {wallet_id} obtenida desde cache.")
            return self.cache[wallet_id]
        
        logger.info(f"Obteniendo datos del cluster {wallet_id} para análisis heurístico...")
        try:
            wallet_transactions = self.client.get_wallet_transactions(wallet_id, from_idx=0, count=100)
            
            if not wallet_transactions:
                logger.warning(f"No se obtuvieron transacciones para cluster {wallet_id}")
                return self._unknown_result(wallet_id)
            
            wallet_addresses = self.client.get_wallet_addresses(wallet_id, from_idaddr=0, count=100)
            
            wallet_data = {
                'txs': wallet_transactions.get('txs', []),
                'n_addresses': wallet_addresses.get('addresses_count', 0),
                'txs_count': wallet_transactions.get('txs_count', 0)
            }
            
            logger.debug(f"Cluster {wallet_id}: {wallet_data['n_addresses']} direcciones, {wallet_data['txs_count']} txs totales")
            
            result = self._analyze_cluster_patterns(wallet_id, wallet_data)
            self.cache[wallet_id] = result
            
            logger.info(f"Cluster {wallet_id} clasificado como '{result['cluster_type']}' (confianza: {result['confidence']:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Error clasificando cluster {wallet_id}: {e}")
            return self._error_result(str(e))
    
    def _classify_from_label(self, wallet_id: str, label: str) -> Dict:
        """
        Clasifica basándose en la label de WalletExplorer (máxima confianza).
        """
        label_lower = label.lower()
        
        # Buscar en mapeos conocidos
        for cluster_type, keywords in self.LABEL_MAPPINGS.items():
            if any(keyword in label_lower for keyword in keywords):
                logger.info(f"Label '{label}' mapeada a tipo '{cluster_type}'")
                return self._build_result(cluster_type, 0.95, wallet_id, label=label,
                    description= f'Identificado por WalletExplorer: {label}')
        
        # Label no mapeada, clasificar como entity con alta confianza
        logger.debug(f"Label '{label}' no mapeada, clasificando como 'labeled_entity'")
        return self._build_result('labeled_entity', 0.9, wallet_id, label=label,
            description= f'Entidad etiquetada: {label}')
    
    def _analyze_cluster_patterns(self, wallet_id: str, wallet_data: Dict) -> Dict:
        """
        Aplica heurísticas basadas en patrones agregados del cluster (sin label).
        """
        txs = wallet_data.get('txs', [])
        query_n_txs = len(txs)
        total_txs = wallet_data.get('txs_count', 0)
        total_addresses = wallet_data.get('n_addresses', 0)
        
        logger.debug(f"Analizando patrones: {query_n_txs} txs obtenidas de {total_txs} totales")
        
        if query_n_txs == 0:
            logger.warning(f"Cluster {wallet_id} sin transacciones registradas")
            return self._build_result('inactive', 0.9, wallet_id, label="",
                description='Cluster sin transacciones registradas')
        
        # Separar por tipo
        received = [tx for tx in txs if tx.get('type') == 'received']
        sent = [tx for tx in txs if tx.get('type') == 'sent']
        
        # Métricas
        sent_with_outputs = [tx for tx in sent if tx.get('outputs')]
        avg_outputs = sum(len(tx.get('outputs', [])) for tx in sent_with_outputs) / len(sent_with_outputs) if sent_with_outputs else 0
        ratio_received = len(received) / query_n_txs if query_n_txs > 0 else 0
        avg_amount = sum(tx.get('amount', 0) for tx in txs) / query_n_txs if query_n_txs > 0 else 0
        unique_wallets = len(set(tx.get('wallet_id') for tx in txs if tx.get('wallet_id')))
        
        logger.debug(f"Métricas: received={len(received)}, sent={len(sent)}, "
                    f"ratio_recv={ratio_received:.2%}, avg_outputs={avg_outputs:.2f}, "
                    f"unique_wallets={unique_wallets}, avg_amount={avg_amount:.6f} BTC")
        
        # Heurísticas (orden de prioridad)
        if ratio_received > 0.7 and avg_amount < 0.01 and unique_wallets > 50 and total_txs > 500:
            logger.info(f"Heurística Mixer aplicada")
            return self._build_result('mixer', 0.75, wallet_id, label="",
                description= f'Patrón de mixer: {ratio_received:.1%} recibidas, {unique_wallets} wallets')
        
        if total_addresses > 50000 or total_txs > 10000:
            logger.info(f"Heurística Exchange aplicada")
            return self._build_result('exchange', 0.85, wallet_id, label="",
                description= f'Cluster muy grande: {total_addresses} direcciones, {total_txs} txs')
        
        if avg_outputs > 10 and len(sent) > 20:
            logger.info(f"Heurística Payout aplicada")
            return self._build_result('payout_service', 0.7, wallet_id, label="",
                description= f'Patrón de distribución: avg {avg_outputs:.1f} outputs/tx')
        
        if ratio_received < 0.3 and total_txs > 100:
            logger.info(f"Heurística Mining/Consolidation aplicada")
            return self._build_result('mining_or_consolidation', 0.65, wallet_id, label="",
                description= f'Patrón de minería: {ratio_received:.1%} recibidas')
        
        if total_addresses > 50 or total_txs > 100:
            logger.info(f"Heurística Entity aplicada")
            return self._build_result('entity', 0.5, wallet_id,label="",
                description= f'Entidad con {total_addresses} direcciones, {total_txs} txs')
        
        logger.info(f"Heurística Personal Wallet aplicada")
        return self._build_result('personal_wallet', 0.6, wallet_id, label="",
            description= f'Cluster pequeño: {total_addresses} direcciones, {total_txs} txs')
    
    def _build_result(self, cluster_type: str, confidence: float,wallet_id: str, label: str, 
                      description: str) -> Dict:
        return {
            'cluster_type': cluster_type,
            'wallet_id': wallet_id,
            'confidence': confidence,
            'label': label,
            'description': description
        }
    
    def _unknown_result(self, wallet_id: str) -> Dict:
        logger.warning(f"Resultado desconocido para cluster {wallet_id}")
        return self._build_result('unknown', 0.0, wallet_id, label="",
            description='No se pudo obtener datos del cluster')
    
    def _error_result(self, error: str) -> Dict:
        return {
            'cluster_type': 'error',
            'wallet_id': None,
            'confidence': 0.0,
            'label': "",
            'description': f'Error: {error}'
        }
