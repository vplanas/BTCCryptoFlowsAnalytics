import sys
from src.utils.logger import get_logger
from src.tracer.tracer import Tracer
from src.export.export import export_fund_flow_records_to_csv
from config import THRESHOLD, MAX_HOPS, BLOCKCHAIR_API_KEY, BLOCKCYPHER_API_KEY

logger = get_logger(__name__)

# El punto de inicio del analisis viene dado por la dirección raíz y el bloque en el que la dirección recibió los fondos por primera vez.
# El primer paso es obtener los flujos recibidos en esa dirección en ese bloque y luego rastrear rastrear los flujos salientes en transaciones posteriores.
def main():
    if len(sys.argv) == 3:
        root_address = sys.argv[1]
        start_block = int(sys.argv[2])
    else:
        #root_address = "15JFh88FcE4WL6qeMLgX5VEAFCbRXjc9fr"  # ejemplo dirección para test darkside vs colonial
        #start_block = 682599 # ejemplo bloque para test es el bloque en el que se enviaron los BTC que queremos seguir a la dirección root_address
        root_address = "bc1q8ssu2xvl8gj3qctz9d3qjfkcmdyxledp40hyp6"  # ejemplo dirección para test
        start_block = 920802


    logger.info(f"{"*"*20} EMPEZANDO ANÁLISIS DE DIRECCIÓN RAÍZ: {root_address} {"*"*20}")

    tracer = Tracer(root_address=root_address, threshold=THRESHOLD, blockchair_api_key=BLOCKCHAIR_API_KEY, blockcypher_api_key=BLOCKCYPHER_API_KEY, maxhops=MAX_HOPS)
    tracer.trace(address=root_address, start_block=start_block)
    export_fund_flow_records_to_csv(tracer.fund_flow_records, 'output/fund_flow_records.csv')

    # Exportar a CSV a la carpeta output con fechas_nombreFichero.csv
    logger.info(f"{"*"*20} ANÁLISIS COMPLETADO. RESULTADOS GUARDADOS EN 'output/fund_flow_records.csv' {"*"*20}")

if __name__ == "__main__":
    main()