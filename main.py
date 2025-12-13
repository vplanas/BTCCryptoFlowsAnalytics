import sys
import json
import argparse
from pathlib import Path
from src.utils.logger import get_logger
from src.tracer.tracer import Tracer
from src.export.export import export_fund_flow_records_to_csv
from src.visualization.graph_html_generator import GraphHTMLGenerator
from src.utils.cache import *
from config import THRESHOLD, MAX_HOPS, BLOCKCHAIR_API_KEY, BLOCKCYPHER_API_KEY

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Bitcoin Flow Tracker")
    parser.add_argument('address', nargs='?', help='Root Bitcoin address')
    parser.add_argument('block', nargs='?', type=int, help='Starting block height')
    parser.add_argument('--from-cache', '-c', help='Load from cache file')
    parser.add_argument('--list-cache', '-l', action='store_true', help='List available cache files')
    parser.add_argument('--clear-cache', action='store_true', help='Clear all cache files')
    
    #Ejemplo de uso:
        # python main.py bc1qexampleaddress 920802
        # python main.py --from-cache cache_abc123.json
        # python main.py --list-cache
        # python main.py --clear-cache
    args = parser.parse_args()
    
    tracer = None

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
        cached_data = load_cache(args.from_cache)
        if not cached_data:
            logger.error("No se pudo cargar el cache")
            return
        
        root_address = cached_data['root_address']
        records = cached_data['records']
        graph_data = cached_data['graph']
        
        logger.info(f"Cargados {len(records)} registros desde cache")
    
    # No se carga desde cache, iniciar nuevo tracing
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

        # Obtener registros y grafo

        records = tracer.fund_flow_records
        graph_data = tracer.get_graph_data()
        
        # Guardar en cache
        records_cache_file = save_cache(records, graph_data, root_address)
        logger.info(f"Cache guardado en: {records_cache_file}")
    
    # Exportar CSV
    fund_flow_records_csv_path = Path('output/fund_flow_records.csv')
    export_fund_flow_records_to_csv(records, str(fund_flow_records_csv_path))

    # Exportar grafo a JSON
    graph_json_path = Path('output/fund_flow_graph.json')
    with open(graph_json_path, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)
    
    # Generar visualización HTML desde el grafo JSON
    html_generator = GraphHTMLGenerator(graph_data)
    html_generator.generate('output/fund_flow_graph.html')
    
    logger.info(f"{'*'*20} ANALISIS COMPLETADO {'*'*20}")


if __name__ == "__main__":
    main()
