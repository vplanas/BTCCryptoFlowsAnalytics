import logging
from config import LOG_LEVELS

def get_logger(name):
    # Crea un logger con el nombre del módulo.
    short_name = _get_short_name(name)
    logger = logging.getLogger(short_name)
    # Por defecto, pongo el nivel de log a WARNING, pero lo sobreescribo si está en la configuración.
    logger.setLevel(LOG_LEVELS.get(name, logging.DEBUG))
    # Limpia cualquier handler existente para evitar duplicados o bloqueos
    if logger.hasHandlers():
        logger.handlers.clear()

    # Crea un handler que manda los mensajes a consola (stdout).
    ch = logging.StreamHandler()
    # Define formato fecha, nombre logger, nivel y mensaje para los logs.
    formatter = logging.Formatter('[%(asctime)s %(name)s::%(levelname)s] %(message)s',
                                  datefmt='%Y%m%d %H:%M:%S'  # formato de fecha YYYYMMDD HH:MM:SS
                                  )
    # Aplica ese formato al handler
    ch.setFormatter(formatter)
    # Asocia el handler al logger
    logger.addHandler(ch)

    return logger

def _get_short_name(name):
    """
    Dado un nombre de módulo completo, devuelve solo el nombre base. Si tiene __ __, los elimina.
    Ejemplo: 'src.apiClients.blockchair_client' -> 'blockchair_client'
    """
    base_name = name.split('.')[-1]
    if base_name.startswith('__') and base_name.endswith('__'):
        # Si el nombre base está entre __ __, lo eliminamos.
        base_name = base_name[2:-2]
    return base_name
