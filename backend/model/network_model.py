# network_model.py
from .host import Host
from .switch import Switch
from .link import Link
import json
from datetime import datetime

class NetworkModel:
    """
    Class chính, đại diện cho toàn bộ "Tấm gương" Digital Twin.
    Nó là một vật chứa (container) lưu trữ và quản lý tất cả các
    đối tượng Host, Switch, và Link.
    """
    
    def __init__(self, name):
        """
        Hàm khởi tạo cho mô hình mạng.
        
        Args:
            name (str): Tên của mô hình (ví dụ: 'MyUniversityNetwork').
        """
        self.name = name
        
        # Chúng ta sử dụng Dictionary (bảng băm) để lưu trữ các đối tượng.
        # Điều này cho phép truy cập rất nhanh bằng tên (ví dụ: 'h1', 's1').
        # { 'h1': <Host object ...>, 'h2': <Host object ...> }
        self.hosts = {}
        
        # { 's1': <Switch object ...>, 's2': <Switch object ...> }
        self.switches = {}
        
        # { 'h1-s1': <Link object ...>, 's1-s2': <Link object ...> }
        self.links = {}
        
        print(f"Khởi tạo NetworkModel: {self.name}")

    # --- Các phương thức Thêm (Add) ---
    
    def add_host(self, name, ip_address, mac_address):
        """Tạo và thêm một Host mới vào mô hình."""
        if name in self.hosts:
            print(f"[Lỗi] Host '{name}' đã tồn tại.")
            return None
        
        new_host = Host(name, ip_address, mac_address)
        self.hosts[name] = new_host
        print(f"[{self.name}] Đã thêm Host: {name}")
        return new_host

    def add_switch(self, name, dpid):
        """Tạo và thêm một Switch mới vào mô hình."""
        if name in self.switches:
            print(f"[Lỗi] Switch '{name}' đã tồn tại.")
            return None
            
        new_switch = Switch(name, dpid)
        self.switches[name] = new_switch
        print(f"[{self.name}] Đã thêm Switch: {name}")
        return new_switch

    def add_link(self, node1_name, node2_name, bandwidth_capacity=100.0):
        """Tạo và thêm một Link mới vào mô hình."""
        link_id = f"{node1_name}-{node2_name}"
        reverse_link_id = f"{node2_name}-{node1_name}"
        
        if link_id in self.links or reverse_link_id in self.links:
            print(f"[Lỗi] Link giữa '{node1_name}' và '{node2_name}' đã tồn tại.")
            return None
            
        # Kiểm tra xem cả hai node có tồn tại không
        if (node1_name not in self.hosts and node1_name not in self.switches) or \
           (node2_name not in self.hosts and node2_name not in self.switches):
            print(f"[Lỗi] Không thể tạo link. Node '{node1_name}' hoặc '{node2_name}' không tồn tại.")
            return None

        new_link = Link(node1_name, node2_name, bandwidth_capacity)
        self.links[link_id] = new_link
        print(f"[{self.name}] Đã thêm Link: {link_id}")
        return new_link

    # --- Các phương thức Truy cập (Get) ---

    def get_host(self, name):
        """Lấy một đối tượng Host bằng tên của nó."""
        return self.hosts.get(name)

    def get_switch(self, name):
        """Lấy một đối tượng Switch bằng tên của nó."""
        return self.switches.get(name)

    def get_link(self, node1_name, node2_name):
        """Lấy một đối tượng Link bằng tên của hai node."""
        link_id = f"{node1_name}-{node2_name}"
        reverse_link_id = f"{node2_name}-{node1_name}"
        return self.links.get(link_id) or self.links.get(reverse_link_id)

    def get_all_nodes(self):
        """Trả về một danh sách tất cả các đối tượng Host và Switch."""
        return list(self.hosts.values()) + list(self.switches.values())

    # --- Phương thức "Toàn cảnh" (The 'Big Picture' Method) ---

    def get_network_snapshot(self):
        """
        Tạo một "ảnh chụp nhanh" (snapshot) toàn bộ mạng.
        Đây là dữ liệu JSON bạn sẽ gửi cho Dashboard!
        """
        
        # 1. Chuyển đổi tất cả các đối tượng thành JSON
        json_hosts = [host.to_json() for host in self.hosts.values()]
        json_switches = [switch.to_json() for switch in self.switches.values()]
        json_links = [link.to_json() for link in self.links.values()]
        
        # 2. Xây dựng cấu trúc cho Dashboard (ví dụ: D3.js, Vis.js)
        # Các thư viện này thường cần 2 danh sách: 'nodes' và 'edges'
        
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
            
        # 'edges' chính là 'links'
        edges_for_graph = []
        for link in json_links:
            edges_for_graph.append({
                'id': link['id'],
                'from': link['node1'],
                'to': link['node2'],
                'label': f"{link['current_throughput']:.1f} Mbps",
                'details': link
            })

        # 3. Gói tất cả lại
        snapshot = {
            'model_name': self.name,
            'timestamp': datetime.now().isoformat(),
            'total_hosts': len(self.hosts),
            'total_switches': len(self.switches),
            'total_links': len(self.links),
            'graph_data': {
                'nodes': nodes_for_graph,
                'edges': edges_for_graph
            },
            # 'raw_data': { # Bạn cũng có thể gửi dữ liệu thô
            #     'hosts': json_hosts,
            #     'switches': json_switches,
            #     'links': json_links
            # }
        }
        return snapshot