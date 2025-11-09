from typing import List, Tuple, Dict, Union
import pytz # Para manejo de zonas horarias
from datetime import datetime
import csv
from src.utils.logger import get_logger
from src.apiClients.blockchair_client import BlockchairClient
from src.models.fund_flow_record import FundFlowRecord

SAT_PER_BTC = 100_000_000 # Satoshis en un Bitcoin

logger = get_logger(__name__)

class Tracer:
    def __init__(self, threshold: float, blockchair_api_key: str, maxhops: int):
        self.client = BlockchairClient(blockchair_api_key)
        self.threshold = threshold
        self.maxhops = maxhops
        self.case_total_input_btc = 0
        self.root_address = ""
        self.fund_flow_records: List[FundFlowRecord] = []

    def trace(self, address: str , start_block: int = 0, hop: int = 1, following_btcs: float = 0.0, path: int = 0):
        # Usar los valores iniciales de address y start_block si no se proporcionan como parametros
        if start_block is None:
            start_block = self.start_block
        if hop == 1:
            self.root_address = address

        logger.info(f"(path:{path}, hop:{hop}) Rastreo de la dirección: {address}")

        # Obtener información básica de la dirección
        addr_info = self.client.get_address_info(address)
        if not addr_info:
            logger.warning("No se pudo obtener información de la dirección.")
            return

        balance = addr_info.get('address', {}).get('balance', 0) / SAT_PER_BTC
        n_tx = addr_info.get('address', {}).get('transaction_count', 0)
        logger.info(f"Saldo de {address}: {balance} BTC, Número de transacciones: {n_tx}")
    
        # Obtener transacciones filtradas desde start_block
        txs = self.client.get_all_transactions(address, start_block, max_records=100)
        if not txs:
            logger.warning("No se encontraron transacciones después del bloque especificado.")
            return

        #logger.debug(f"Transacciones: {txs}")

        # Procesar hop 1 (especial para la dirección raíz) obteniendo total de BTC recibidos
        if hop == 1:
            hop_1_data = self.__hop_1_info(txs, address, start_block)
            logger.info(f"Es hop 1: Se obtienen detalles.Total recibido por {address} en bloque {start_block}: {hop_1_data['total_input_btc']} BTC en {hop_1_data['fecha_transaccion']}, valor USD: {hop_1_data['total_usd']}")
            # Guardamos el total de BTC recibidos en el hop 1 para calcular umbrales relativos
            self.case_total_input_btc = hop_1_data['total_input_btc']

        # Identificar salidas en transacciones que tengan la direccion seguida como entrada y que superan el umbral transacciones de bloques posteriores al start_block
        outputs_to_follow, outputs_after_flow, btc_not_followed = self.__get_outputs_to_follow(txs, address, self.case_total_input_btc, self.case_total_input_btc if hop == 1 else following_btcs)
        logger.debug(f"Outputs a seguir: {outputs_to_follow}")
        logger.debug(f"Outputs después del flujo: {outputs_after_flow}")
        logger.info(f"(path:{path}, hop:{hop}) Número de outputs a seguir: {len(outputs_to_follow)}")
        logger.info(f"(path:{path}, hop:{hop}) Número de outputs no seguidos después de gastar los BTC recibidos: {len(outputs_after_flow)}")
        logger.info(f"(path:{path}, hop:{hop}) BTC no seguidos en este hop por no superar umbral: {btc_not_followed} BTC")

        # Seguir cada output que supera el umbral
        #el primero seguirá el current path y los demas seran nuevos paths path+1
        for i, output in enumerate(outputs_to_follow):
            next_address = output['recipient']
            value_btc = output['value_btc']
            child_path = path if i == 0 else path + i  # Path secuencialmente para cada output extra
            # Llamada recursiva para el siguiente hop mientras no se supere el número máximo de hops
            if hop+1 <= self.maxhops:
                logger.info(f"(path:{child_path}, hop:{hop}) Siguiendo output a {next_address} con {value_btc} BTC desde tx {output['tx_hash']} a partir del bloque {output['block_id']}")
                self.trace(address=next_address, start_block=output['block_id'], hop=hop+1, following_btcs=value_btc, path=child_path)
            else:
                logger.info(f"(path:{child_path}, hop:{hop+1}) Máximo número de hops ({self.maxhops}) alcanzado. No se seguirá hacia la siguiente dirección ({next_address}) por este path.")

            # Registrar el FundFlowRecord para este hop
            record = FundFlowRecord(
                seed_case=self.root_address,
                path_id=child_path,
                hop=hop,
                follow=True,
                input=address,
                output=next_address,
                wallet_explorer_id="",
                wallet_classification="",
                dest_tag="",
                txid="",
                datetime_CET=output['datetime_CET'],
                mov_type="OUT",
                BTC=value_btc,  
                classification="",
                BTC_added_to_flow_from_others= 0.0,     # BTC añadidos al seguimiento desde otras fuentes
                BTC_not_followed= btc_not_followed,     # BTC en este hop no seguidos explícitamente
                notes= ""                               # Comentarios o notas adicionales
                        )
            self.fund_flow_records.append(record)
    
    def __hop_1_info(self, txs: list, address: str, start_block: int) -> dict:
        """
        Información detallada para el hop 1 (primer hop).
        """
        # Si estamos en el hop 1, calcular el total de BTC en las entradas para esta dirección
        initial_txs = [tx for tx in txs if tx.get('block_id') == start_block]
        #logger.debug(f"Transacciones en el bloque inicial {start_block}: {initial_txs}")

        recibo_inicial = self.__get_address_received_info_from_txs(initial_txs, address)
        total_input_btc = recibo_inicial['total_btc']   
        return {
            'total_input_btc': total_input_btc, 
            'fecha_transaccion': recibo_inicial['fecha_transaccion'],
            'total_usd': recibo_inicial['total_usd']
        }

    def __get_address_received_info_from_txs(self, txs: list, address: str) -> dict:
        """
        Calcula el total recibido por la dirección y devuelve la fecha y valor en USD
        tomando como referencia las salidas (outputs) en las transacciones.
        """
        total_recibido_satoshis = 0
        fecha_transaccion = None
        total_recibido_usd = 0.0

        for tx in txs:
            detalles = tx.get('details', {})
            outputs = detalles.get('outputs', [])

            for output in outputs:
                if output.get('recipient') == address:
                    total_recibido_satoshis += output.get('value', 0)
                    fecha_transaccion = tx.get('time')
                    total_recibido_usd += output.get('value_usd', 0.0)

        return {
            'total_satoshis': total_recibido_satoshis,
            'total_btc': total_recibido_satoshis / SAT_PER_BTC,
            'fecha_transaccion': fecha_transaccion,
            'total_usd': total_recibido_usd
        }

    def __get_outputs_to_follow(self, txs: list, from_address: str, total_input_btc: int, btc_received: int) -> Tuple[List[Dict], List[Dict], float]:
        """
        Dada una lista de transacciones y una dirección de entrada, devuelve las salidas que superan el umbral
        hasta que se ha gastado los BTC que ha recibido la dirección del flujo seguido.
        """
        outputs_to_follow = []
        outputs_after_flow = []
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
                    logger.debug(f"Evaluando output a {outp.get('recipient')} con {btc_out} BTC en tx {tx.get('hash')} - btc_output_accumulated: {btc_output_accumulated}, btc_received: {btc_received} en tx con fee {fee} BTC")
                    if btc_output_accumulated <= (btc_received-fee):
                        if btc_out / total_input_btc > self.threshold:
                            # Añadir la dirección de la salida y la cantidad recibida a la lista de seguimiento como un diccionario
                            outputs_to_follow.append({
                                'tx_hash': tx.get('hash'),
                                'recipient': outp.get('recipient'),
                                'value': outp.get('value', 0),
                                'value_btc': btc_out,
                                'value_usd': outp.get('value_usd', 0),
                                'block_id': tx.get('block_id'),
                                'datetime_CET': dt_cet
                            })
                        else:
                            logger.debug(f"Output a {outp.get('recipient')} con {btc_out} BTC no supera el umbral del {self.threshold*100}% del total recibido ({total_input_btc} BTC). Se suman a BTCs no seguidos.")
                            btc_not_followed += btc_out
                        btc_output_accumulated += btc_out
                    else:
                        logger.debug(f"Ya se han seguido BTCs por un total de {btc_output_accumulated} BTC, que supera los {btc_received - fee} BTC recibidos (menos fee). No se sigue el output a {outp.get('recipient')} con {btc_out} BTC. Pero se registran")
                        outputs_after_flow.append({
                            'tx_hash': tx.get('hash'),
                            'recipient': outp.get('recipient'),
                            'value': outp.get('value', 0),
                            'value_btc': btc_out,
                            'value_usd': outp.get('value_usd', 0),
                            'block_id': tx.get('block_id'),
                            'datetime_CET': dt_cet
                        })

        # Ordenamos los outputs a seguir por cantidad descendente, asi el primero seguirá el current path y los demas seran nuevos paths path+1
        outputs_to_follow.sort(key=lambda x: x['value_btc'], reverse=True)
        return outputs_to_follow, outputs_after_flow, btc_not_followed
    
    def fund_flow_records_to_csv(self, filepath: str):
        # Exporta los registros de flujo de fondos a un archivo CSV
        with open(filepath, mode='w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'seed_case', 'path_id', 'hop', 'follow', 'input', 'output', 'wallet_explorer_id',
                'wallet_classification', 'dest_tag', 'txid', 'datetime_CET', 'mov_type', 'BTC',
                'classification', 'BTC_added_to_flow_from_others', 'BTC_not_followed', 'notes'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for record in self.fund_flow_records:

                writer.writerow({
                    'seed_case': record.seed_case,
                    'path_id': record.path_id,
                    'hop': record.hop,
                    'follow': record.follow,
                    'input': record.input,
                    'output': record.output,
                    'wallet_explorer_id': record.wallet_explorer_id,
                    'wallet_classification': record.wallet_classification,
                    'dest_tag': record.dest_tag,
                    'txid': record.txid,
                    'datetime_CET': record.datetime_CET.strftime('%Y-%m-%d %H:%M:%S'),
                    'mov_type': record.mov_type,
                    'BTC': record.BTC,
                    'classification': record.classification,
                    'BTC_added_to_flow_from_others': record.BTC_added_to_flow_from_others,
                    'BTC_not_followed': record.BTC_not_followed,
                    'notes': record.notes
                })



    
        