import os
import json
from mininet.topo import Topo
from utils.logger import setup_logger

logger = setup_logger()

class ConfigTopo(Topo):
    def build(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # SỬA ĐỔI: Thêm một '..' vì file này nằm sâu hơn file cũ 1 cấp (trong thư mục core)
        # Cấu trúc: mininet_twin/core/topo.py -> mininet_twin/core -> mininet_twin -> Root Project
        config_path = os.path.abspath(os.path.join(current_dir, '..', '..', 'topology.json'))

        try:
            with open(config_path) as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"[LỖI] Không thể đọc file topology.json: {e}")
            return

        host_nodes = {}
        switch_nodes = {}

        # Thêm hosts
        for host in config.get('hosts', []):
            h = self.addHost(host['name'], ip=host['ip'], mac=host.get('mac'))
            host_nodes[host['name']] = h

        # Thêm switches
        for switch in config.get('switches', []):
            s = self.addSwitch(switch['name'], dpid=switch.get('dpid'))
            switch_nodes[switch['name']] = s

        # Thêm links
        for link in config.get('links', []):
            node1 = host_nodes.get(link['from']) or switch_nodes.get(link['from'])
            node2 = host_nodes.get(link['to']) or switch_nodes.get(link['to'])
            if node1 and node2:
                self.addLink(node1, node2, bw=link.get('bw', 100))
            else:
                logger.error(f"[Lỗi Topo] Node không tồn tại: {link['from']} - {link['to']}")