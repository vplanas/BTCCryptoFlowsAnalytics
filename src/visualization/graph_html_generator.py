"""
Genera un HTML simple e intuitivo desde un grafo JSON (node_link_data).
Sin pyvis, usando vis.js directamente con layout jerárquico.
El nodo seed estará a la izquierda y la red se expande hacia la derecha.

Usa plantillas Jinja2 para separar HTML de la lógica Python.
"""
from pathlib import Path
import json
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GraphHTMLGenerator:
    """
    Genera visualización HTML de un grafo Bitcoin desde datos node_link_data.
    - Recibe: dict con 'nodes' y 'links' (formato networkx json_graph.node_link_data)
    - Genera: HTML con vis.js, layout jerárquico, nodo seed a la izquierda
    - Usa plantilla Jinja2 para mantener HTML separado del código Python
    """

    def __init__(self, graph_data: Dict[str, Any], title: str = "Bitcoin Flow Graph"):
        """
        Inicializa el generador.
        
        Args:
            graph_data: dict con estructura {'nodes': [...], 'links': [...]} o {'nodes': [...], 'edges': [...]}
            title: título del HTML
        """
        # Normalizar el formato: networkx usa 'edges', vis.js usa 'links'
        if 'edges' in graph_data and 'links' not in graph_data:
            graph_data['links'] = graph_data['edges']
        
        self.graph_data = graph_data
        self.title = title

    def generate(self, output_file: str = "output/fund_flow_graph.html") -> Path:
        """
        Genera el archivo HTML con la visualización.
        Carga la plantilla desde templates/graph_template.html.jinja2 y la renderiza con Jinja2.
        
        Args:
            output_file: ruta donde guardar el HTML
            
        Returns:
            Path al archivo generado
        """
        # Crear directorio de salida si no existe
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convertir graph_data a JSON string para embeber en HTML
        # ensure_ascii=False preserva caracteres especiales
        graph_data_json = json.dumps(self.graph_data, ensure_ascii=False)

        # Cargar plantilla Jinja2
        template_dir = Path(__file__).parent / "templates"
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("graph_template.html.jinja2")

        # Renderizar plantilla con contexto
        html_content = template.render(
            title=self.title,
            graph_data_json=graph_data_json
        )

        # Escribir el HTML a archivo
        output_path.write_text(html_content, encoding="utf-8")
        logger.info(f"HTML generado: {output_path}")
        logger.debug(f"  Nodos: {len(self.graph_data.get('nodes', []))}")
        logger.debug(f"  Enlaces: {len(self.graph_data.get('links', []))}")
        
        return output_path
