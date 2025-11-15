import json
import os
from typing import List
from datetime import datetime
from dataclasses import asdict
from src.models.fund_flow_record import FundFlowRecord
from src.utils.logger import get_logger

logger = get_logger(__name__)

CACHE_DIR = "output/cache"


def save_records_to_cache(records: List[FundFlowRecord], root_address: str, cache_file: str = None):
    """
    Guarda los registros de flujo en cache (JSON).
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    if not cache_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cache_file = f"{CACHE_DIR}/flow_records_{root_address[:10]}_{timestamp}.json"
    
    try:
        # Convertir FundFlowRecords a diccionarios
        records_dict = [asdict(record) for record in records]
        
        cache_data = {
            'root_address': root_address,
            'timestamp': datetime.now().isoformat(),
            'total_records': len(records),
            'records': records_dict
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"{len(records)} registros guardados en cache: {cache_file}")
        return cache_file
    except Exception as e:
        logger.error(f"Error guardando cache: {e}")
        return None


def load_records_from_cache(cache_file: str) -> dict:
    """
    Carga registros desde cache (JSON).
    Retorna dict con 'root_address', 'timestamp', 'records'.
    """
    if not os.path.exists(f"{CACHE_DIR}/{cache_file}"):
        logger.error(f"Archivo de cache no encontrado: {cache_file}")
        return None
    
    try:
        with open(f"{CACHE_DIR}/{cache_file}", 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # Reconstruir FundFlowRecords desde diccionarios
        # hay que trasnformar las fechas de string a datetime

        records = []
        for record_data in cache_data['records']:
            # Convertir datetime_CET de string a datetime
            datetime_str = record_data.get('datetime_CET')
            if datetime_str:
                # Parsear el string con timezone
                datetime_cet = datetime.fromisoformat(datetime_str)
            else:
                datetime_cet = None
            
            record = FundFlowRecord(
                seed_case=record_data['seed_case'],
                path_id=record_data['path_id'],
                hop=record_data['hop'],
                follow=record_data['follow'],
                input=record_data['input'],
                output=record_data['output'],
                wallet_explorer_id=record_data['wallet_explorer_id'],
                wallet_classification=record_data['wallet_classification'],
                wallet_label=record_data.get('wallet_label', ''),
                txid=record_data['txid'],
                datetime_CET=datetime_cet,  # Ahora es datetime, no string
                mov_type=record_data['mov_type'],
                BTC=record_data['BTC'],
                classification=record_data['classification'],
                BTC_added_to_flow_from_others=record_data['BTC_added_to_flow_from_others'],
                BTC_not_followed=record_data['BTC_not_followed'],
                notes=record_data['notes']
            )
            records.append(record)
            
            result = {
                'root_address': cache_data['root_address'],
                'timestamp': cache_data['timestamp'],
                'records': records
            }

        logger.info(f"{len(records)} registros cargados desde cache: {cache_file}")
        logger.info(f"Root address: {result['root_address']}, Timestamp: {result['timestamp']}")
        return result
    except Exception as e:
        logger.error(f"Error cargando cache: {e}")
        return None


def list_cache_files():
    """Lista archivos de cache disponibles."""
    if not os.path.exists(CACHE_DIR):
        logger.warning(f"Directorio de cache no existe: {CACHE_DIR}")
        return []
    
    cache_files = [f for f in os.listdir(CACHE_DIR) if f.endswith('.json')]
    
    if not cache_files:
        logger.info("No hay archivos de cache disponibles.")
        return []
    
    logger.info(f"Archivos de cache disponibles: {len(cache_files)}")
    for f in cache_files:
        full_path = os.path.join(CACHE_DIR, f)
        size_mb = os.path.getsize(full_path) / (1024 * 1024)
        
        # Leer metadata del JSON
        try:
            with open(full_path, 'r') as file:
                data = json.load(file)
                timestamp = data.get('timestamp', 'N/A')
                root = data.get('root_address', 'N/A')
                records_count = data.get('total_records', 0)
            logger.info(f"  - {f}")
            logger.info(f"    Size: {size_mb:.2f} MB")
            logger.info(f"    Root: {root}")
            logger.info(f"    Records: {records_count}")
            logger.info(f"    Timestamp: {timestamp}")
        except:
            logger.info(f"  - {f} ({size_mb:.2f} MB) - Error leyendo metadata")
    
    return cache_files


def delete_cache_file(cache_file: str):
    """Elimina un archivo de cache."""
    try:
        if os.path.exists(f"{CACHE_DIR}/{cache_file}"):
            os.remove(f"{CACHE_DIR}/{cache_file}")
            logger.info(f"Cache eliminado: {cache_file}")
            return True
        else:
            logger.warning(f"Cache no encontrado: {cache_file}")
            return False
    except Exception as e:
        logger.error(f"Error eliminando cache: {e}")
        return False


def clear_all_cache():
    """Elimina todos los archivos de cache."""
    if not os.path.exists(CACHE_DIR):
        logger.warning(f"Directorio de cache no existe: {CACHE_DIR}")
        return 0
    
    cache_files = [os.path.join(CACHE_DIR, f) for f in os.listdir(CACHE_DIR) if f.endswith('.json')]
    
    if not cache_files:
        logger.info("No hay archivos de cache para eliminar.")
        return 0
    
    deleted = 0
    for cache_file in cache_files:
        if delete_cache_file(cache_file):
            deleted += 1
    
    logger.info(f"{deleted} archivos de cache eliminados")
    return deleted
