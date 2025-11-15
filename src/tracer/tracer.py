from typing import List, Tuple, Dict, Union
import pytz # Para manejo de zonas horarias
from datetime import datetime
from src.utils.logger import get_logger
from src.apiClients.blockchair_client import BlockchairClient
from src.apiClients.blockcypher_client import BlockCypherClient
from src.models.fund_flow_record import FundFlowRecord
from src.cluster_heuristics.cluster_heuristics import ClusterHeuristics
from config import STOP_TRACE_ACTIONS_BY_WALLET_CLASSIFICATION
import json

SAT_PER_BTC = 100_000_000 # Satoshis en un Bitcoin

logger = get_logger(__name__)

class Tracer:
    # Inicializa el tracer con los parámetros necesarios
    def __init__(self, root_address: str, threshold: float, blockchair_api_key: str, blockcypher_api_key: str, maxhops: int):
        self.BlockChairClient = BlockchairClient(blockchair_api_key) # Cliente para interactuar con la API de Blockchair
        self.BlockCypherClient = BlockCypherClient(blockcypher_api_key)  # Cliente para interactuar con la API de Blockcypher (pendiente de implementar)
        self.heuristics = ClusterHeuristics() # Cliente para clasificación de clusters
        self.threshold = threshold # Umbral para seguir flujos (fracción del total recibido)
        self.maxhops = maxhops # Número máximo de saltos para rastrear  
        self.case_total_input_btc = 0 # Total de BTC recibidos en el hop 1 (dirección raíz)
        self.root_address = root_address # Dirección raíz del análisis
        self.fund_flow_records: List[FundFlowRecord] = [] # Registros de flujos de fondos rastreados

    def trace(self, address: str , start_block: int = 0, hop: int = 1, following_btcs: float = 0.0, path: int = 0):
        # from_address: dirección desde la que se recibió el BTC en el hop anterior (None si es la raíz)
        logger.info(f"(path:{path}, hop:{hop}) Rastreo de la dirección: {address}")

        # Obtener información básica de la dirección
        addr_info = self.BlockChairClient.get_address_info(address)
        if not addr_info:
            logger.warning("No se pudo obtener información de la dirección.")
            return

        balance = addr_info.get('address', {}).get('balance', 0) / SAT_PER_BTC
        n_tx = addr_info.get('address', {}).get('transaction_count', 0)
        logger.info(f"Saldo de {address}: {balance:.10f} BTC, Número de transacciones: {n_tx}")

        # Obtenemos (Máximo 100) transacciones desde start_block usando Blockchair
        txs, limit_reached = self.BlockChairClient.get_all_transactions(address, start_block, max_records=100)
        if limit_reached:
            logger.warning(f"(path:{path}, hop:{hop}) Atención: Se ha alcanzado el límite máximo de registros al obtener transacciones para {address}. Es posible que no se hayan contabilizado todas las transacciones.")
        if not txs:
            logger.warning("No se encontraron transacciones después del bloque especificado.")
            return
        
        #print(json.dumps(txs, indent=2, ensure_ascii=False))

        # Obtener transacciones filtradas desde start_block
        # Usamos la Api de Blockcypher, mucho mas eficiente para encontrar transacciones posteriores a un bloque dado
        #txs2 = self.BlockCypherClient.get_txs_between_blocks(address,after=start_block-1,before=start_block+1)
        #print(json.dumps(txs2, indent=2, ensure_ascii=False))

        # Procesar hop 1 (especial para la dirección raíz) obteniendo total de BTC recibidos
        if hop == 1:
            # De las transacciones obtenidas, calculamos el total recibido en el bloque inicial start_block
            hop_1_data = self.__hop_1_info(txs, address, start_block)
            logger.debug(f"Es hop 1: Se obtienen detalles del total recibido en el inicio de la investigación --->")
            logger.debug(f"--->{address} en bloque {start_block} recibió {hop_1_data['total_input_btc']} BTC | fecha {hop_1_data['transaction_date']}, valor USD: {hop_1_data['total_usd']}")
            # Guardamos el total de BTC recibidos en el hop 1 para calcular umbrales relativos
            self.case_total_input_btc = hop_1_data['total_input_btc']

        '''
        Intento de capturar BTC recibidos desde bloque 0 para cada dirección. Es muy costoso en tiempo y llamadas API
        else:
            logger.debug(f"(path:{path}, hop:{hop})Obtenemos el total de BTC recibidos por {address} des del principio (bloque 0)")
            receipt_info = self.__btc_received_by_address_on_txs_since_block(address, start_block=0)
            logger.debug(f"--->{address} desde bloque 0 ha recibido un total de {receipt_info['total_input_btc']} BTC | fecha {receipt_info['transaction_date']}, valor USD: {receipt_info['total_usd']}")
            funds_from_others = receipt_info['total_input_btc']-following_btcs
            if receipt_info['limit_reached']:
                logger.warning(f"(path:{path}, hop:{hop}) Atención: Se ha alcanzado el límite máximo de registros al obtener transacciones para {address}. Es posible que no se hayan contabilizado todos los BTC recibidos.")
            logger.info(f"(path:{path}, hop:{hop}) A parte de los {following_btcs:.10f} BTC recibidos en el hop anterior, {address} ha recibido un total de {funds_from_others:.10f} BTC desde el bloque 0")
        '''

        # Identificar salidas en transacciones que tengan la direccion 'actual' (address) como entrada y que superan el umbral en transacciones de bloques posteriores al start_block
        txs_outputs_to_follow, txs_outputs_after_flow, btc_not_followed = self.__get_outputs_to_follow(txs, address, self.case_total_input_btc, self.case_total_input_btc if hop == 1 else following_btcs)
        logger.debug(f"Outputs a seguir: {txs_outputs_to_follow}")
        logger.debug(f"Outputs después del flujo: {txs_outputs_after_flow}")
        logger.info(f"(path:{path}, hop:{hop}) Número de outputs a seguir: {len(txs_outputs_to_follow)}")
        logger.info(f"(path:{path}, hop:{hop}) Número de outputs no seguidos después de gastar los BTC recibidos: {len(txs_outputs_after_flow)}")
        logger.info(f"(path:{path}, hop:{hop}) BTC no seguidos en este hop por no superar umbral: {btc_not_followed:.10f} BTC") if btc_not_followed > 0 else None

        # Seguir cada output que supera el umbral
        # el primero que encontremos seguirá por el current path y los demas seran nuevos paths path+1
        for i, output in enumerate(txs_outputs_to_follow):
            next_address = output['recipient']
            value_btc = output['value_btc']
            child_path = path if i == 0 else path + i  # Path secuencialmente para cada output extra

            # Aplicamos heurísticas de clasificación de cluster para la doreccón siguiente
            # Buscamos la dirección en WalletExplorer para ver si pertenece a un cluster conocido, aplicamos heurísticas y obtenemos la clasificación
            classification = self.heuristics.classify_address(next_address)
            logger.info(f"(path:{path}, hop:{hop}) Clasificación de cluster para {next_address}: Tipo: {classification['cluster_type']}, Confianza: {classification['confidence']:.2%}, Descripción: {classification['description']}, Label: {classification.get('label', 'N/A')}")

            # Decidir si seguir
            should_follow = (
                hop + 1 <= self.maxhops and 
                classification['cluster_type'] not in STOP_TRACE_ACTIONS_BY_WALLET_CLASSIFICATION
            )
            # Llamada recursiva para el siguiente hop mientras no se supere el número máximo de hops o haya una clasificación que indique detenerse
            if should_follow:
                logger.info(f"(path:{child_path}, hop:{hop}) Siguiendo output a {next_address} con {value_btc:.10f} BTC desde tx {output['tx_hash']} a partir del bloque {output['block_id']}")
                self.trace(address=next_address, start_block=output['block_id'], hop=hop+1, following_btcs=value_btc, path=child_path)
            else:
                logger.info(f"(path:{child_path}, hop:{hop}) No se seguirá hacia la siguiente dirección ({next_address}) por este path. {classification['cluster_type']} o max hops. No se seguirá hacia la siguiente dirección ({next_address}) por este path.")

            # Registrar el FundFlowRecord para este hop
            record = FundFlowRecord(
                seed_case=self.root_address,
                path_id=child_path,
                hop=hop,
                follow=should_follow,
                input=address,
                output=next_address,
                wallet_explorer_id=classification.get('wallet_id', "N/A"),
                wallet_classification=classification.get('cluster_type', "N/A"),
                wallet_label=classification.get('label', ""),
                txid=output['tx_hash'],
                datetime_CET=output['datetime_CET'],
                mov_type="OUT",
                BTC=value_btc,  
                classification="",
                BTC_added_to_flow_from_others= 0.0,     # BTC añadidos al seguimiento desde otras fuentes
                BTC_not_followed= btc_not_followed,     # BTC en este hop no seguidos explícitamente
                notes= "" if should_follow else f"No seguido: {classification['cluster_type']}"                               # Comentarios o notas adicionales
                        )
            self.fund_flow_records.append(record)
        

    def __btc_received_by_address_on_txs_since_block(self, address: str, start_block: int) -> dict:
        txs_since_block,limit_reached = self.BlockChairClient.get_all_transactions(address=address, start_block=start_block,max_records=20)
        logger.debug(f"Transacciones  desde el bloque {start_block}: {len(txs_since_block)}")

        # Calcular el total de BTC recibido en las transacciones desde el bloque
        receipt_info = self.__get_address_received_info_from_txs(txs_since_block, address)
        return {
            'total_input_btc': receipt_info['total_btc'],
            'transaction_date': receipt_info['transaction_date'],
            'total_usd': receipt_info['total_usd'],
            'limit_reached': limit_reached
        }

    def __hop_1_info(self, txs: list, address: str, start_block: int) -> dict:
        """
        Información detallada para el hop 1 (primer hop).
        """
        # Si estamos en el hop 1, calcular el total de BTC en las entradas para esta dirección en el bloque inicial inidcado
        # de ese modo podremos obtener el valor total recibido en el punto donde empezamos a seguir el flujo
        logger.info(f"(Hop 1) Calculando total recibido por {address} en el bloque {start_block} mirando en {len(txs)} transacciones.")
        #logger.debug(f"Transacciones recibidas para hop 1: {txs}")
        txs_in_startblock = [tx for tx in txs if tx.get('block_id') == start_block]
        #logger.debug(f"Transacciones en el bloque inicial {start_block}: {initial_txs}")

        # Obtener información de recibo para el hop 1
        receipt_info = self.__get_address_received_info_from_txs(txs_in_startblock, address)
        total_input_btc = receipt_info['total_btc']   
        return {
            'total_input_btc': total_input_btc, 
            'transaction_date': receipt_info['transaction_date'],
            'total_usd': receipt_info['total_usd']
        }

    def __get_address_received_info_from_txs(self, txs: list, address: str) -> dict:
        """
        Calcula el total recibido por la dirección en una lista de transacciones y devuelve la fecha y valor en USD
        tomando como referencia las salidas (outputs) en las transacciones.
        """
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

    def __get_outputs_to_follow(self, txs: list, from_address: str, total_input_btc: int, btc_received: int) -> Tuple[List[Dict], List[Dict], float]:
        """
        Dada una lista de transacciones y una dirección de entrada, devuelve las salidas que superan el umbral
        hasta que se ha gastado los BTC que ha recibido la dirección del flujo seguido.
        """
        txs_outputs_to_follow = []
        txs_outputs_after_flow = []
        btc_output_accumulated = 0
        btc_not_followed = 0
        # Hay que ordenar las transacciones por bloque ascendente para procesarlas en orden cronológico
        txs.sort(key=lambda tx: tx.get('block_id', 0))
        for tx in txs:
            detalles = tx.get('details', {})
            inputs = detalles.get('inputs', [])
            outputs = detalles.get('outputs', [])
            fee = detalles.get('fee', 0)/SAT_PER_BTC
            # Parsear datetime de UTC a CET
            dt_naive = datetime.strptime(tx.get('time'), '%Y-%m-%d %H:%M:%S')
            dt_cet = dt_naive.astimezone(pytz.timezone('CET'))

            # Verificar si la dirección está entre las entradas
            if any(inp.get('recipient') == from_address for inp in inputs):
                # Es una transaccion OUT desde la direccion seguida
                for outp in outputs:
                    satoshis_out = outp.get('value', 0)
                    btc_out = satoshis_out / SAT_PER_BTC
                    # Si ya hemos acumulado todo lo que la dirección ha recibido, los siguientes outputs no se siguen
                    logger.debug(f"Evaluando output a {outp.get('recipient')} con {btc_out:.10f} BTC en tx {tx.get('hash')} - btc_output_accumulated: {btc_output_accumulated:.10f}, btc_received: {btc_received:.10f} en tx con fee {fee:.10f} BTC")
                    if btc_output_accumulated <= (btc_received-fee):
                        if btc_out / total_input_btc > self.threshold:
                            # Añadir la dirección de la salida y la cantidad recibida a la lista de seguimiento como un diccionario
                            txs_outputs_to_follow.append({
                                'tx_hash': tx.get('hash'),
                                'recipient': outp.get('recipient'),
                                'value': outp.get('value', 0),
                                'value_btc': btc_out,
                                'value_usd': outp.get('value_usd', 0),
                                'block_id': tx.get('block_id'),
                                'datetime_CET': dt_cet
                            })
                        else:
                            logger.debug(f"Output a {outp.get('recipient')} con {btc_out:.10f} BTC no supera el umbral del {self.threshold*100}% del total recibido ({total_input_btc:.10f} BTC). Se suman a BTCs no seguidos.")
                            btc_not_followed += btc_out
                        btc_output_accumulated += btc_out
                    else:
                        logger.debug(f"Ya se han seguido BTCs por un total de {btc_output_accumulated:.10f} BTC, que supera los {btc_received - fee:.10f} BTC recibidos (menos fee). No se sigue el output a {outp.get('recipient')} con {btc_out:.10f} BTC. Pero se registran")
                        txs_outputs_after_flow.append({
                            'tx_hash': tx.get('hash'),
                            'recipient': outp.get('recipient'),
                            'value': outp.get('value', 0),
                            'value_btc': btc_out,
                            'value_usd': outp.get('value_usd', 0),
                            'block_id': tx.get('block_id'),
                            'datetime_CET': dt_cet
                        })

        # Ordenamos los outputs a seguir por cantidad descendente, asi el primero seguirá el current path y los demas seran nuevos paths path+1
        txs_outputs_to_follow.sort(key=lambda x: x['value_btc'], reverse=True)
        return txs_outputs_to_follow, txs_outputs_after_flow, btc_not_followed 
        