from .host import Host
from .switch import Switch
from .link import Link
import json
from datetime import datetime

class NetworkModel:
    """
    Là nơi lưu trữ và quản lý tất cả các đối tượng Host, Switch, và Link.
    """
    
    def __init__(self, name):
        self.name = name

        self.hosts = {}

        self.switches = {}
        
        self.links = {}
        
        print(f"Khởi tạo NetworkModel: {self.name}")

    
    def add_host(self, name, ip_address, mac_address):
        if name in self.hosts:
            print(f"[Lỗi] Host '{name}' đã tồn tại.")
            return None
        
        new_host = Host(name, ip_address, mac_address)
        self.hosts[name] = new_host
        print(f"[{self.name}] Đã thêm Host: {name}")
        return new_host

    def add_switch(self, name, dpid):
        if name in self.switches:
            print(f"[Lỗi] Switch '{name}' đã tồn tại.")
            return None
            
        new_switch = Switch(name, dpid)
        self.switches[name] = new_switch
        print(f"[{self.name}] Đã thêm Switch: {name}")
        return new_switch

    def add_link(self, node1_name, node2_name, bandwidth_capacity=100.0):
        link_id = "-".join(sorted([node1_name, node2_name]))
        if link_id  in self.links:
            print(f"[Lỗi] Link giữa '{node1_name}' và '{node2_name}' đã tồn tại.")
            return None

        if (node1_name not in self.hosts and node1_name not in self.switches) or \
           (node2_name not in self.hosts and node2_name not in self.switches):
            print(f"[Lỗi] Không thể tạo link. Node '{node1_name}' hoặc '{node2_name}' không tồn tại.")
            return None

        new_link = Link(node1_name, node2_name, bandwidth_capacity)
        self.links[link_id] = new_link
        print(f"[{self.name}] Đã thêm Link: {link_id}")
        return new_link

    def get_host(self, name):
        return self.hosts.get(name)

    def get_switch(self, name):
        return self.switches.get(name)

    def get_link(self, node1_name, node2_name):
        link_id = f"{node1_name}-{node2_name}"
        reverse_link_id = f"{node2_name}-{node1_name}"
        return self.links.get(link_id) or self.links.get(reverse_link_id)

    def get_all_nodes(self):
        return list(self.hosts.values()) + list(self.switches.values())

    def get_network_snapshot(self):
        """
        Tạo một "ảnh chụp nhanh" (snapshot) toàn bộ mạng.
        Đây là dữ liệu JSON bạn sẽ gửi cho Dashboard!
        """
        
        json_hosts = [host.to_json() for host in self.hosts.values()]
        json_switches = [switch.to_json() for switch in self.switches.values()]
        json_links = [link.to_json() for link in self.links.values()]
        
        # 'nodes' bao gồm cả hosts và switches
        nodes_for_graph = []
        for host in json_hosts:
            nodes_for_graph.append({
                'id': host['name'],
                'label': host['name'],
                'group': 'host',
                'details': host
            })
        for switch in json_switches:
            nodes_for_graph.append({
                'id': switch['name'],
                'label': switch['name'],
                'group': 'switch',
                'details': switch
            })
            
        # 'edges'
        edges_for_graph = []
        for link in json_links:
            # [FIX] Nếu link offline/down, không hiển thị throughput
            if link['status'] in ['down', 'offline', 'unknown']:
                label = 'DOWN' if link['status'] == 'down' else 'OFFLINE'
                utilization = 0.0
            else:
                label = f"{link['current_throughput']:.1f} Mbps"
                utilization = link['utilization']
            
            edges_for_graph.append({
                'id': link['id'],
                'from': link['node1'],
                'to': link['node2'],
                'label': label,
                'utilization': utilization,
                'status': link['status'],
                'details': link
            })

        snapshot = {
            'model_name': self.name,
            'timestamp': datetime.now().isoformat(),
            'total_hosts': len(self.hosts),
            'total_switches': len(self.switches),
            'total_links': len(self.links),
            'graph_data': {
                'nodes': nodes_for_graph,
                'edges': edges_for_graph
            }
        }
        return snapshot