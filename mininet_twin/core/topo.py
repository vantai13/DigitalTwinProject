import os
import json
from mininet.topo import Topo
from utils.logger import logger

class ConfigTopo(Topo):
    def build(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.abspath(os.path.join(current_dir, '..', '..', 'topology.json'))

        try:
            with open(config_path) as f:
                config = json.load(f)
        except Exception as e:
            print(f"[LỖI] Không thể đọc file topology.json: {e}")
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
                bw_val = link.get('bw', 100)
        
                # ✅ KHẮC PHỤC LỖI QUANTUM
                # Công thức an toàn: r2q = bw_mbps * 10
                # Ví dụ: 100Mbps -> r2q=1000 -> quantum=12,500 (OK)
                #        1000Mbps -> r2q=10000 -> quantum=12,500 (OK)
                r2q_value = max(100, int(bw_val * 10))
                
                self.addLink(
                    node1, node2,
                    bw=bw_val,
                    delay='1ms',
                    loss=0,
                    use_htb=True,
                    max_queue_size=1000,
                    r2q=r2q_value  # ← QUAN TRỌNG
                )
            else:
                print(f"[Lỗi Topo] Node không tồn tại: {link['from']} - {link['to']}")