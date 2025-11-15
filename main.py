import sys
import argparse
from src.utils.logger import get_logger
from src.tracer.tracer import Tracer
from src.export.export import export_fund_flow_records_to_csv
from src.visualization.flow_graph_visualizer import FlowGraphVisualizer
from src.utils.cache import save_records_to_cache, load_records_from_cache, list_cache_files, clear_all_cache
from config import THRESHOLD, MAX_HOPS, BLOCKCHAIR_API_KEY, BLOCKCYPHER_API_KEY

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Bitcoin Flow Tracker")
    parser.add_argument('address', nargs='?', help='Root Bitcoin address')
    parser.add_argument('block', nargs='?', type=int, help='Starting block height')
    parser.add_argument('--from-cache', '-c', help='Load from cache file')
    parser.add_argument('--list-cache', '-l', action='store_true', help='List available cache files')
    parser.add_argument('--clear-cache', action='store_true', help='Clear all cache files')
    
    args = parser.parse_args()
    
    # Listar cache
    if args.list_cache:
        list_cache_files()
        return
    
    # Limpiar cache
    if args.clear_cache:
        clear_all_cache()
        return
    
    # Cargar desde cache
    if args.from_cache:
        logger.info(f"Cargando desde cache: {args.from_cache}")
        cached_data = load_records_from_cache(args.from_cache)
        if not cached_data:
            logger.error("No se pudo cargar el cache")
            return
        
        root_address = cached_data['root_address']
        records = cached_data['records']
        
        logger.info(f"Cargados {len(records)} registros desde cache")
    
    # Trace normal
    else:
        if not args.address or not args.block:
            # Valores por defecto para testing en un caso de suplantación conocida
            root_address = "bc1q8ssu2xvl8gj3qctz9d3qjfkcmdyxledp40hyp6"
            start_block = 920802
            # Probar con el caso de darkside - colonial pipeline
            #root_address = "15JFh88FcE4WL6qeMLgX5VEAFCbRXjc9fr"
            #start_block = 682599 
            logger.warning(f"Usando valores por defecto: {root_address} @ block {start_block}")
        else:
            root_address = args.address
            start_block = args.block
        
        logger.info(f"{'*'*20} EMPEZANDO ANALISIS DE DIRECCION RAIZ: {root_address} {'*'*20}")
        
        tracer = Tracer(
            root_address=root_address,
            threshold=THRESHOLD,
            blockchair_api_key=BLOCKCHAIR_API_KEY,
            blockcypher_api_key=BLOCKCYPHER_API_KEY,
            maxhops=MAX_HOPS
        )
        tracer.trace(address=root_address, start_block=start_block)
        records = tracer.fund_flow_records
        
        # Guardar en cache
        cache_file = save_records_to_cache(records, root_address)
        logger.info(f"Cache guardado en: {cache_file}")
    
    # Exportar CSV
    export_fund_flow_records_to_csv(records, 'output/fund_flow_records.csv')
    
    # Generar visualizacion
    visualizer = FlowGraphVisualizer(records, root_address)
    visualizer.generate_graph("output/fund_flow_graph.html")
    
    logger.info(f"{'*'*20} ANALISIS COMPLETADO {'*'*20}")


if __name__ == "__main__":
    main()
