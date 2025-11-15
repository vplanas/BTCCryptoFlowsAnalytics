from pyvis.network import Network
from typing import List
from src.models.fund_flow_record import FundFlowRecord
from src.utils.logger import get_logger

logger = get_logger(__name__)

class FlowGraphVisualizer:
    """Genera visualizacion HTML interactiva del flujo de fondos."""
    
    def __init__(self, fund_flow_records: List[FundFlowRecord], root_address: str):
        self.records = fund_flow_records
        self.root_address = root_address
        self.net = Network(height="900px", width="80%", directed=True, bgcolor="#222222", font_color="white")
        self.net.barnes_hut()
        logger.debug("FlowGraphVisualizer inicializado")
        
    def generate_graph(self, output_file: str = "fund_flow_graph.html"):
        """Genera el grafo HTML interactivo."""
        logger.info(f"Generando grafo con {len(self.records)} registros...")
        
        # Añadir nodo raiz
        self.net.add_node(
            self.root_address,
            label=self._truncate_address(self.root_address),
            title=f"ROOT: {self.root_address}",
            color="#FF4136",
            size=30,
            shape="star"
        )
        
        # Set para rastrear nodos ya añadidos
        added_nodes = {self.root_address}
        
        # Añadir nodos y edges
        for record in self.records:
            if record.follow:
                color = self._get_color_by_classification(record.wallet_classification)
                
                if record.input and record.input not in added_nodes:
                    self.net.add_node(
                        record.input,
                        label=self._truncate_address(record.input),
                        title=self._get_node_tooltip(record, "input"),
                        color=color,
                        size=15 + (record.hop * 2),
                        shape="dot"
                    )
                    added_nodes.add(record.input)
                
                if record.output not in added_nodes:
                    self.net.add_node(
                        record.output,
                        label=self._truncate_address(record.output),
                        title=self._get_node_tooltip(record, "output"),
                        color=color,
                        size=15 + (record.hop * 2),
                        shape="dot"
                    )
                    added_nodes.add(record.output)
                
                if record.input:
                    self.net.add_edge(
                        record.input,
                        record.output,
                        value=record.BTC * 10,
                        title=f"Hop {record.hop} | {record.BTC:.6f} BTC | Path {record.path_id}",
                        label=f"{record.BTC:.4f} BTC",
                        color=self._get_edge_color_by_hop(record.hop)
                    )
        
        self.net.set_options("""
        var options = {
          "physics": {
            "barnesHut": {
              "gravitationalConstant": -30000,
              "centralGravity": 0.3,
              "springLength": 200
            }
          },
          "edges": {
            "arrows": {"to": {"enabled": true, "scaleFactor": 0.5}},
            "smooth": {"type": "cubicBezier"}
          }
        }
        """)
        
        self.net.save_graph(output_file)
        self._inject_info_panel(output_file)
        
        logger.info(f"Grafo guardado en: {output_file}")
        return output_file
    
    def _inject_info_panel(self, html_file: str):
        """Inyecta panel lateral de informacion."""
        
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        custom_html = """
        <style>
        body { margin: 0; display: flex; }
        #mynetwork { flex: 1; }
        #info-panel {
            width: 300px;
            background: #1a1a1a;
            color: white;
            padding: 20px;
            font-family: monospace;
            font-size: 12px;
            overflow-y: auto;
            border-left: 2px solid #FF4136;
        }
        #info-panel h3 {
            color: #FF4136;
            margin-top: 0;
        }
        #info-panel .info-row {
            margin: 10px 0;
            word-wrap: break-word;
        }
        #info-panel .label {
            color: #888;
            font-size: 10px;
        }
        #info-panel .value {
            color: #fff;
            font-size: 12px;
        }
        </style>
        
        <script type="text/javascript">
        network.on("click", function(params) {
            if (params.nodes.length > 0) {
                var nodeId = params.nodes[0];
                showNodeInfo(nodeId);
            }
        });
        
        function showNodeInfo(nodeId) {
            var node = network.body.data.nodes.get(nodeId);
            var infoPanel = document.getElementById('info-panel');
            
            var html = '<h3>Node Info</h3>';
            html += '<div class="info-row">';
            html += '<div class="label">ADDRESS</div>';
            html += '<div class="value">' + nodeId + '</div>';
            html += '</div>';
            
            if (node.title) {
                var lines = node.title.split('\\n');
                lines.forEach(function(line) {
                    if (line.includes(':')) {
                        var parts = line.split(':');
                        html += '<div class="info-row">';
                        html += '<div class="label">' + parts[0].trim() + '</div>';
                        html += '<div class="value">' + parts.slice(1).join(':').trim() + '</div>';
                        html += '</div>';
                    }
                });
            }
            
            infoPanel.innerHTML = html;
        }
        </script>
        """
        
        # Cambiar estructura del HTML
        html_content = html_content.replace('<body>', '<body><div id="info-panel"><h3>Node Info</h3><p>Click en un nodo para ver informacion</p></div>')
        html_content = html_content.replace('</body>', custom_html + '</body>')
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _get_node_tooltip(self, record: FundFlowRecord, node_type: str) -> str:
        """Tooltip del nodo."""
        address = record.input if node_type == "input" else record.output
        return (
            f"Address: {address}\n"
            f"Hop: {record.hop}\n"
            f"Path: {record.path_id}\n"
            f"Classification: {record.wallet_classification}\n"
            f"Wallet ID: {record.wallet_explorer_id}\n"
            f"BTC: {record.BTC:.8f}\n"
            f"Date: {record.datetime_CET}"
        )
    
    def _truncate_address(self, address: str, length: int = 10) -> str:
        if len(address) <= length:
            return address
        return f"{address[:6]}...{address[-4:]}"
    
    def _get_color_by_classification(self, classification: str) -> str:
        color_map = {
            'exchange': '#0074D9',
            'mixer': '#B10DC9',
            'mining': '#FF851B',
            'mining_or_consolidation': '#FF851B',
            'gambling': '#FFDC00',
            'darknet': '#85144b',
            'personal_wallet': '#2ECC40',
            'entity': '#AAAAAA',
            'unclustered': '#FFFFFF',
            'labeled_entity': '#39CCCC',
            'payout_service': '#01FF70'
        }
        return color_map.get(classification, '#DDDDDD')
    
    def _get_edge_color_by_hop(self, hop: int) -> str:
        colors = ['#FF4136', '#FF851B', '#FFDC00', '#2ECC40', '#0074D9', '#B10DC9']
        return colors[min(hop - 1, len(colors) - 1)]
