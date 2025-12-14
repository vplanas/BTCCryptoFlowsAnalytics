from typing import List, Tuple, Dict, Union
import pytz # Para manejo de zonas horarias
from datetime import datetime
from src.utils.logger import get_logger
from src.apiClients.blockchair_client import BlockchairClient
from src.apiClients.blockcypher_client import BlockCypherClient
from src.models.fund_flow_record import FundFlowRecord
from src.cluster_heuristics.cluster_heuristics import ClusterHeuristics
from config import STOP_TRACE_ACTIONS_BY_WALLET_CLASSIFICATION
import networkx as nx


SAT_PER_BTC = 100_000_000 # Satoshis en un Bitcoin

logger = get_logger(__name__)

class Tracer:
    """
    Clase que implementa el rastreo recursivo de flujos Bitcoin.
    
    Sigue las transacciones desde una dirección inicial aplicando un umbral de seguimiento
    y usando clasificación de wallets para decidir cuándo parar.
    
    Attributes:
        blockchair_client: Cliente API de Blockchair
        blockcypher_client: Cliente API de BlockCypher (por ahora sin usar)
        heuristics: Clasificador de direcciones y clusters
        threshold: Porcentaje mínimo para seguir un output
        maxhops: Límite de saltos en el rastreo
        case_total_input_btc: BTC totales recibidos en la dirección inicial
        root_address: Dirección inicial del caso
        fund_flow_records: Lista con todos los movimientos detectados
        G: Grafo de NetworkX con los flujos
        next_path_id: ID para identificar cada rama del flujo
        btc_not_followed_outputs: Outputs que no se siguieron (y por qué)
    """
    
    def __init__(self, root_address: str, threshold: float, blockchair_api_key: str, blockcypher_api_key: str, maxhops: int):
        """
        Inicializa el tracer con los parámetros del caso.
        
        Args:
            root_address: Dirección donde empieza el rastreo
            threshold: Umbral (0-1) para seguir outputs
            blockchair_api_key: Key de Blockchair
            blockcypher_api_key: Key de BlockCypher
            maxhops: Máximo de saltos a seguir
        """
        self.blockchair_client = BlockchairClient(blockchair_api_key)
        self.blockcypher_client = BlockCypherClient(blockcypher_api_key)
        self.heuristics = ClusterHeuristics()
        self.threshold = threshold
        self.maxhops = maxhops
        self.case_total_input_btc = 0
        self.root_address = root_address
        self.fund_flow_records: List[FundFlowRecord] = []
        self.G = nx.DiGraph()
        self.next_path_id = 0
        self.btc_not_followed_outputs = []

    def trace(self, address: str, start_block: int = 0, hop: int = 1, following_btcs: float = 0.0, path: int = 0, previous_tx_hash: str = None, previous_vout: int = None):
        """
        Función recursiva principal del rastreo.
        
        Obtiene las txs de una dirección, mira qué outputs superan el umbral,
        y los va siguiendo recursivamente hasta llegar al maxhops o encontrar
        un exchange/wallet conocido donde parar.
        
        Args:
            address: Dirección a rastrear en este hop
            start_block: Bloque desde donde buscar transacciones
            hop: Número de salto (empieza en 1)
            following_btcs: Cuántos BTC estamos siguiendo
            path: ID del camino actual
            previous_tx_hash: Hash de la tx anterior (para seguir UTXO concreto)
            previous_vout: Índice del output anterior
        """
        logger.info(f"(path:{path}, hop:{hop}) Rastreo de la dirección: {address}")

        # Obtenemos las txs desde blockchair (limitamos a 200 para no saturar)
        txs, limit_reached = self.blockchair_client.get_all_transactions(address, start_block, max_records=200)
        if limit_reached:
            logger.warning(f"(path:{path}, hop:{hop}) Atención: alcanzado límite de 200 txs para {address}. Puede que falten datos.")
        if not txs:
            logger.warning("No hay transacciones después de ese bloque.")
            return
        
        # TODO: En el futuro usar BlockCypher que es más eficiente para buscar txs por rango de bloques

        # Si es el primer hop, calculamos el total recibido para usarlo como referencia
        if hop == 1:
            self.next_path_id = 1  # Los paths siguientes serán 1, 2, 3...
            hop_1_data = self.__hop_1_info(txs, address, start_block)
            logger.debug(f"Hop inicial: {address} recibió {hop_1_data['total_input_btc']} BTC en bloque {start_block}")
            logger.debug(f"Fecha: {hop_1_data['transaction_date']}, valor USD: {hop_1_data['total_usd']}")
            self.case_total_input_btc = hop_1_data['total_input_btc']  # Esto lo usaremos para calcular umbrales

        # Buscamos qué outputs seguir (los que superan el umbral)
        txs_outputs_to_follow, txs_outputs_after_flow, btc_not_followed = self.__get_outputs_to_follow(
            txs, address, self.case_total_input_btc, 
            self.case_total_input_btc if hop == 1 else following_btcs,
            previous_tx_hash=previous_tx_hash,
            previous_vout=previous_vout
        )

        logger.info(f"(path:{path}, hop:{hop}) Outputs a seguir: {len(txs_outputs_to_follow)}")
        logger.info(f"(path:{path}, hop:{hop}) Outputs ignorados (ya gastado todo): {len(txs_outputs_after_flow)}")
        if btc_not_followed > 0:
            logger.info(f"(path:{path}, hop:{hop}) BTC no seguidos (bajo umbral): {btc_not_followed:.10f} BTC")

        # Procesamos cada output que vamos a seguir
        for i, output in enumerate(txs_outputs_to_follow):
            self.__process_output(output, i, path, hop, address, btc_not_followed)

    def __assign_path_id(self, is_first: bool, current_path: int) -> int:
        """El primer output sigue el path actual, los demás crean nuevas ramas."""
        if is_first:
            return current_path
        else:
            path_id = self.next_path_id
            self.next_path_id += 1
            return path_id
    
    def __get_or_classify_address(self, address: str, path: int, hop: int) -> dict:
        """Devuelve la clasificación de una dirección, reusando del grafo si ya la teníamos."""
        if self.G.has_node(address):
            logger.debug(f"(path:{path}, hop:{hop}) Ya habíamos clasificado {address}, reusamos datos")
            # Los nodos guardan wallet_classification, pero el resto del código espera cluster_type
            node_data = self.G.nodes[address]
            return {
                'cluster_type': node_data.get('wallet_classification', 'N/A'),
                'wallet_id': node_data.get('wallet_explorer_id', 'N/A'),
                'label': node_data.get('wallet_label', ''),
                'confidence': node_data.get('confidence', 0),
                'description': node_data.get('description', '')
            }
        else:
            classification = self.heuristics.classify_address(address)
            logger.info(f"(path:{path}, hop:{hop}) Clasificación de cluster para {address}: Tipo: {classification['cluster_type']}, Confianza: {classification['confidence']:.2%}, Descripción: {classification['description']}, Label: {classification.get('label', 'N/A')}")
            return classification
    
    def __should_follow_address(self, classification: dict, hop: int) -> bool:
        """Mira si debemos seguir esta dirección (no hemos llegado al límite y no es exchange)."""
        return (
            hop + 1 <= self.maxhops and 
            classification['cluster_type'] not in STOP_TRACE_ACTIONS_BY_WALLET_CLASSIFICATION
        )
    
    def __add_graph_node(self, address: str, classification: dict):
        """Añade nodo al grafo (si no está ya)."""
        if not self.G.has_node(address):
            self.G.add_node(address,
                label=f"{address[:3]}...{address[-3:]}",
                address=address,
                wallet_explorer_id=classification.get('wallet_id', "N/A"),
                wallet_classification=classification.get('cluster_type', "N/A"),
                wallet_label=classification.get('label', ""),
                confidence=classification.get('confidence', 0),
                description=classification.get('description', "")
            )
    
    def __add_graph_edge(self, from_address: str, to_address: str, output: dict, child_path: int, hop: int, should_follow: bool, btc_not_followed: float):
        """Crea la arista entre dos direcciones con los datos de la tx."""
        value_btc = output['value_btc']
        edge_notes = "" if should_follow else f"No seguido: {output.get('classification_type', 'N/A')}"
        
        self.G.add_edge(from_address, to_address,
            label=f"{value_btc:.8f} BTC (path: {child_path}, hop: {hop})",
            value_btc=value_btc,
            txid=output['tx_hash'],
            datetime=output['datetime_CET'].strftime('%Y-%m-%d %H:%M:%S'),
            hop=hop,
            path_id=child_path,
            follow=should_follow,
            btc_not_followed=btc_not_followed,
            btc_added_from_others=output.get('btc_added_from_others', 0.0),
            notes=edge_notes,
            width=value_btc
        )
    
    def __process_output(self, output: dict, index: int, path: int, hop: int, from_address: str, btc_not_followed: float):
        """Procesa un output individual: clasifica, decide si seguir, crea registros y actualiza el grafo.
           Si procede, llama recursivamente a trace para el siguiente hop.
        """
        next_address = output['recipient']
        value_btc = output['value_btc']
        
        child_path = self.__assign_path_id(is_first=(index == 0), current_path=path)
        classification = self.__get_or_classify_address(next_address, path, hop)
        should_follow = self.__should_follow_address(classification, hop)
        
        # Si toca seguir, hacemos la llamada recursiva
        if should_follow:
            logger.info(f"(path:{child_path}, hop:{hop}) Llamando tracer recursivamente para el output a {next_address} con {value_btc:.10f} BTC desde tx {output['tx_hash']} a partir del bloque {output['block_id']}")
            output_vout = output.get('vout', 0)
            self.trace(address=next_address, start_block=output['block_id'], hop=hop+1, following_btcs=value_btc, path=child_path, previous_tx_hash=output['tx_hash'], previous_vout=output_vout)
        else:
            logger.info(f"(path:{child_path}, hop:{hop}) No se seguirá: {classification['cluster_type']} o maxhops alcanzado")
        
        # Crear FundFlowRecord
        record = FundFlowRecord(
            seed_case=self.root_address,
            path_id=child_path,
            hop=hop,
            follow=should_follow,
            input=from_address,
            output=next_address,
            wallet_explorer_id=classification.get('wallet_id', "N/A"),
            wallet_classification=classification.get('cluster_type', "N/A"),
            wallet_label=classification.get('label', ""),
            txid=output['tx_hash'],
            datetime_CET=output['datetime_CET'],
            mov_type="OUT",
            BTC=value_btc,
            classification="",
            BTC_added_to_flow_from_others=output.get('btc_added_from_others', 0.0),
            BTC_not_followed=btc_not_followed,
            notes="" if should_follow else f"No seguido: {classification['cluster_type']}"
        )
        self.fund_flow_records.append(record)
        
        # Añadir nodos from y toal grafo
        classification_from = self.__get_or_classify_address(from_address, path, hop)
        self.__add_graph_node(from_address, classification_from)
        self.__add_graph_node(next_address, classification)
        
        # Añadir arista
        output['classification_type'] = classification.get('cluster_type', 'N/A')
        self.__add_graph_edge(from_address, next_address, output, child_path, hop, should_follow, btc_not_followed)
    
    def __hop_1_info(self, txs: list, address: str, start_block: int) -> dict:
        """Calcula cuántos BTC recibió la dirección inicial en el bloque de inicio."""
        logger.info(f"(Hop 0) Viendo cuánto recibió {address} en bloque {start_block} ({len(txs)} txs)")
        txs_in_startblock = [tx for tx in txs if tx.get('block_id') == start_block]

        receipt_info = self.__get_address_received_info_from_txs(txs_in_startblock, address)
        logger.debug(f"(Hop 0) Total recibido: {receipt_info['total_btc']} BTC")
        logger.debug(f"----> Fecha: {receipt_info['transaction_date']}, valor USD: {receipt_info['total_usd']}")
        total_input_btc = receipt_info['total_btc']   
        return {
            'total_input_btc': total_input_btc, 
            'transaction_date': receipt_info['transaction_date'],
            'total_usd': receipt_info['total_usd']
        }

    def __get_address_received_info_from_txs(self, txs: list, address: str) -> dict:
        """Suma los BTC recibidos por la dirección en las txs (mirando outputs)."""
        total_recibido_satoshis = 0
        transaction_date = None
        total_recibido_usd = 0.0

        for tx in txs:
            detalles = tx.get('details', {})
            outputs = detalles.get('outputs', [])

            for output in outputs:
                if output.get('recipient') == address:
                    total_recibido_satoshis += output.get('value', 0)
                    transaction_date = tx.get('time')
                    total_recibido_usd += output.get('value_usd', 0.0)

        return {
            'total_satoshis': total_recibido_satoshis,
            'total_btc': total_recibido_satoshis / SAT_PER_BTC,
            'transaction_date': transaction_date,
            'total_usd': total_recibido_usd
        }

    def __get_outputs_to_follow(self, txs: list, from_address: str, total_input_btc: int, btc_received: int, previous_tx_hash: str = None, previous_vout: int = None) -> Tuple[List[Dict], List[Dict], float]:
        """
        Encuentra qué outputs hay que seguir (los que superen el umbral).
        
        Mira las txs donde from_address gasta BTC, y devuelve los outputs que superan
        el threshold. Si previous_tx_hash no es None, solo mira txs que gasten ese UTXO concreto.
        
        Returns: (outputs_a_seguir, outputs_posteriores, btc_no_seguidos)
        """
        txs_outputs_to_follow = []
        txs_outputs_after_flow = []
        btc_output_accumulated = 0
        btc_not_followed = 0
        
        txs.sort(key=lambda tx: tx.get('block_id', 0))  # Ordenamos por bloque
        
        for tx in txs:
            detalles = tx.get('details', {})
            inputs = detalles.get('inputs', [])
            outputs = detalles.get('outputs', [])
            
            # Convertimos la fecha a CET
            dt_naive = datetime.strptime(tx.get('time'), '%Y-%m-%d %H:%M:%S')
            dt_cet = dt_naive.astimezone(pytz.timezone('CET'))

            # Miramos si from_address está gastando en esta tx
            if any(inp.get('recipient') == from_address for inp in inputs):
                # Si estamos siguiendo un UTXO concreto, verificamos que esta tx lo use
                if previous_tx_hash and previous_vout is not None:
                    uses_target_utxo = any(
                        inp.get('previous_txid') == previous_tx_hash and
                        inp.get('previous_output_index') == previous_vout
                        for inp in inputs
                    )
                    if not uses_target_utxo:
                        logger.debug(f"Tx {tx.get('hash')} no usa el UTXO que estamos siguiendo, skip")
                        continue
                    else:
                        logger.debug(f"Tx {tx.get('hash')} sí usa el UTXO {previous_tx_hash}:{previous_vout}")
                
                # Si ya gastamos todo lo que íbamos siguiendo, esta tx ya no nos interesa
                if btc_output_accumulated >= btc_received:
                    logger.debug(f"Ya gastamos todo ({btc_output_accumulated:.10f} >= {btc_received:.10f}), skip")
                    continue
                
                # Ver cuántos BTC se añaden de otras direcciones (consolidación)
                btc_consolidation = self.__calculate_consolidation(inputs, from_address)
                
                # Miramos cada output
                for out_index, outp in enumerate(outputs):
                    satoshis_out = outp.get('value', 0)
                    btc_out = satoshis_out / SAT_PER_BTC
                    recipient = outp.get('recipient')
                    
                    # Ignoramos outputs que son change (vuelven a la misma dirección)
                    # Importante: no descontamos este BTC del acumulado para no perder cobertura
                    if recipient == from_address:
                        logger.debug(f"Output a {recipient} es change, lo ignoramos ({btc_out:.10f} BTC)")
                        # No sumamos al acumulado ni a no-seguidos; solo lo saltamos
                        continue
                    
                    remaining_to_spend = btc_received - btc_output_accumulated
                    logger.debug(f"Output a {recipient}: {btc_out:.10f} BTC (acumulado: {btc_output_accumulated:.10f}, queda: {remaining_to_spend:.10f})")
                    
                    if remaining_to_spend > 0:
                        if btc_out / total_input_btc > self.threshold:
                            logger.debug(f"Output supera umbral {self.threshold*100}%, lo seguimos")
                            # Añadir la dirección de la salida y la cantidad recibida a la lista de seguimiento como un diccionario
                            txs_outputs_to_follow.append({
                                'tx_hash': tx.get('hash'),
                                'recipient': recipient,
                                'value': outp.get('value', 0),
                                'value_btc': btc_out,
                                'value_usd': outp.get('value_usd', 0),
                                'block_id': tx.get('block_id'),
                                'datetime_CET': dt_cet,
                                'btc_added_from_others': btc_consolidation,
                                'vout': out_index
                            })
                        else:
                            logger.debug(f"Output no supera umbral, no lo seguimos")
                            btc_not_followed += btc_out
                            self.btc_not_followed_outputs.append({
                                'from_address': from_address,
                                'to_address': recipient,
                                'btc': btc_out,
                                'reason': f'No supera umbral {self.threshold*100:.1f}%',
                                'tx_hash': tx.get('hash'),
                                'block_id': tx.get('block_id'),
                                'datetime': dt_cet.strftime('%Y-%m-%d %H:%M:%S')
                            })
                        btc_output_accumulated += btc_out
                    else:
                        logger.debug(f"Ya no quedan BTC por seguir, pero registramos este output")
                        txs_outputs_after_flow.append({
                            'tx_hash': tx.get('hash'),
                            'recipient': recipient,
                            'value': outp.get('value', 0),
                            'value_btc': btc_out,
                            'value_usd': outp.get('value_usd', 0),
                            'block_id': tx.get('block_id'),
                            'datetime_CET': dt_cet
                        })

        # Ordenamos por cantidad (el mayor sigue el path actual)
        txs_outputs_to_follow.sort(key=lambda x: x['value_btc'], reverse=True)
        return txs_outputs_to_follow, txs_outputs_after_flow, btc_not_followed
    
    def __calculate_consolidation(self, inputs: list, from_address: str) -> float:
        """Suma BTC que vienen de otras direcciones (inputs externos)."""
        btc_consolidation = 0.0
        for inp in inputs:
            if inp.get('recipient') != from_address:
                btc_consolidation += inp.get('value', 0) / SAT_PER_BTC
        return btc_consolidation 
        
    def get_graph_data(self) -> dict:
        """Devuelve el grafo en formato JSON para visualizar."""
        return nx.json_graph.node_link_data(self.G)
    
    def log_btc_not_followed_summary(self):
        """Muestra resumen de BTC que no seguimos y por qué."""
        total_not_followed = sum(o['btc'] for o in self.btc_not_followed_outputs)
        logger.info(f"\n{'='*60}")
        logger.info(f"RESUMEN DE BTC NO SEGUIDOS:")
        logger.info(f"  Total BTC no seguidos: {total_not_followed:.8f} BTC")
        logger.info(f"  Número de outputs no seguidos: {len(self.btc_not_followed_outputs)}")
        
        reasons_count = {}
        reasons_btc = {}
        for output in self.btc_not_followed_outputs:
            reason = output['reason']
            reasons_count[reason] = reasons_count.get(reason, 0) + 1
            reasons_btc[reason] = reasons_btc.get(reason, 0.0) + output['btc']
        logger.info(f"Desglose por motivo:")
        for reason in sorted(reasons_count.keys()):
            logger.info(f"    {reason}: {reasons_count[reason]} outputs, {reasons_btc[reason]:.8f} BTC")
        logger.info(f"{'='*60}\n")