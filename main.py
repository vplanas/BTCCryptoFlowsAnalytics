import sys
import json
import argparse
from pathlib import Path
from src.utils.logger import get_logger, setup_file_logging
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
        # python main.py bc1q8ssu2xvl8gj3qctz9d3qjfkcmdyxledp40hyp6 920802
        # python main.py --from-cache cache_abc123.json
        # python main.py --list-cache
        # python main.py --clear-cache
    args = parser.parse_args()
    
    tracer = None

    # Listar archivos en cache
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
        start_block = cached_data.get('start_block', 0)
        records = cached_data['records']
        graph_data = cached_data['graph']
        
        logger.info(f"Cargados {len(records)} registros desde cache")
    
    # Hacer un análisis nuevo
    else:
        if not args.address or not args.block:
            # Casos de prueba (descomentar el que se quiera usar):
            # Suplantación:
            #root_address = "bc1q8ssu2xvl8gj3qctz9d3qjfkcmdyxledp40hyp6"
            #start_block = 920802
            # Darkside - Colonial Pipeline:
            root_address = "15JFh88FcE4WL6qeMLgX5VEAFCbRXjc9fr"
            start_block = 682599
            # Otro ransomware:
            #root_address = "bc1qazjzkd4e572p8c2n4u0gaewhrwe8xxpaklq6fv"
            #start_block = 777026
            
            logger.warning(f"Usando dirección de prueba: {root_address} @ bloque {start_block}")
        else:
            root_address = args.address
            start_block = args.block
    
    # Crear carpeta de salida específica para esta investigación y configurar logging
    output_dir_name = f"{root_address[:3]}...{root_address[-3:]}_{start_block}"
    output_dir = Path('output') / output_dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    setup_file_logging(str(output_dir))
    
    logger.info(f"Carpeta de salida: {output_dir}")
    
    # Si cargamos desde cache, ya tenemos los datos; si no, hacemos el análisis
    if not args.from_cache:
        logger.info(f"{'*'*20} EMPEZANDO ANÁLISIS: {root_address} {'*'*20}")
        
        tracer = Tracer(
            root_address=root_address,
            threshold=THRESHOLD,
            blockchair_api_key=BLOCKCHAIR_API_KEY,
            blockcypher_api_key=BLOCKCYPHER_API_KEY,
            maxhops=MAX_HOPS
        )
        tracer.trace(address=root_address, start_block=start_block)

        records = tracer.fund_flow_records
        graph_data = tracer.get_graph_data()
        
        # Guardamos en cache para no tener que volver a analizar
        records_cache_file = save_cache(records, graph_data, root_address, start_block)
        logger.info(f"Cache guardado en: {records_cache_file}")
    
    # Exportar resultados en la carpeta específica
    fund_flow_records_csv_path = output_dir / 'fund_flow_records.csv'
    export_fund_flow_records_to_csv(records, str(fund_flow_records_csv_path))

    graph_json_path = output_dir / 'fund_flow_graph.json'
    with open(graph_json_path, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)
    
    # Generar HTML interactivo del grafo
    html_generator = GraphHTMLGenerator(root_address, graph_data, title="Bitcoin Fund Flow Graph")
    html_generator.generate(str(output_dir / 'fund_flow_graph.html'))
    logger.info(f"Grafo HTML para dirección raíz {root_address} generado en: {output_dir / 'fund_flow_graph.html'}")
    
    # Mostrar resumen (solo si hicimos análisis nuevo)
    if tracer:
        tracer.log_btc_not_followed_summary()
    
    logger.info(f"{'*'*20} ANÁLISIS COMPLETADO {'*'*20}")


if __name__ == "__main__":
    main()
