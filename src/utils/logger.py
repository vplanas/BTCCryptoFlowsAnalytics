import logging
import os
from datetime import datetime
from config import LOG_LEVELS

# Handler de archivo compartido entre todos los loggers
_file_handler = None

class ShortNameFilter(logging.Filter):
    '''Filtro para añadir el nombre corto del módulo a los logs.'''
    def __init__(self, shortname):
        super().__init__()
        self.shortname = shortname

    def filter(self, record):
        record.shortname = self.shortname
        return True

def setup_file_logging(output_dir):
    """Configura el archivo de log en el directorio especificado."""
    global _file_handler
    
    if _file_handler:
        return  # Ya está configurado
    
    os.makedirs(output_dir, exist_ok=True)
    log_filename = f"trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_path = os.path.join(output_dir, log_filename)
    
    _file_handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    
    # Añadir el file handler a todos los loggers existentes
    for logger_name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        if logger.handlers and not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
            # Copiar formato del primer handler (console)
            if logger.handlers:
                formatter = logger.handlers[0].formatter
                _file_handler.setFormatter(formatter)
            logger.addHandler(_file_handler)

def get_logger(name):
    # Crea un logger con el nombre del módulo.
    short_name = _get_short_name(name)
    logger = logging.getLogger(name)
    # Por defecto, pongo el nivel de log a WARNING, pero lo sobreescribo si está en la configuración.
    logger.setLevel(LOG_LEVELS.get(name, logging.DEBUG))
    # Limpia cualquier handler existente para evitar duplicados o bloqueos
    if logger.hasHandlers():
        logger.handlers.clear()

    # Define formato fecha, nombre logger, nivel y mensaje para los logs.
    if LOG_LEVELS.get(name, logging.DEBUG) == logging.DEBUG:
        formatter = logging.Formatter('[%(asctime)s %(shortname)s (%(funcName)s)::%(levelname)s] %(message)s',
                                    datefmt='%Y%m%d %H:%M:%S'  # formato de fecha YYYYMMDD HH:MM:SS
                                    )
    else:
        formatter = logging.Formatter('[%(asctime)s %(shortname)s::%(levelname)s] %(message)s',
                                    datefmt='%Y%m%d %H:%M:%S'  # formato de fecha YYYYMMDD HH:MM:SS
                                    )

    # Handler para consola (stdout)
    ch = logging.StreamHandler()
    ch.addFilter(ShortNameFilter(short_name))
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Si ya existe el file handler global, añadirlo
    if _file_handler:
        fh_filter = ShortNameFilter(short_name)
        _file_handler.addFilter(fh_filter)
        _file_handler.setFormatter(formatter)
        logger.addHandler(_file_handler)

    return logger

def _get_short_name(name):
    """Devuelve solo el nombre base del módulo (sin 'src.xxx.')."""
    base_name = name.split('.')[-1]
    if base_name.startswith('__') and base_name.endswith('__'):
        # Si el nombre base está entre __ __, lo eliminamos.
        base_name = base_name[2:-2]
    return base_name
