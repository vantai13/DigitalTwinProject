from datetime import datetime
class Switch:
    def __init__(self, name, dpid):
        """
            name (str): Tên của switch
            dpid (str): Datapath ID. Đây là một định danh duy nhất
                        của Open vSwitch, rất quan trọng để điều khiển.
        """

        self.name = name
        self.dpid = dpid

        self.status = 'unknown' 

        self.last_update_time = None
        
        # Danh sách các cổng (ports) mà switch này đang kết nối
        self.port_list = []
        
        # Bảng luồng (Flow Table)
        # chúng ta chỉ lưu một danh sách các luồng (flows).
        # Mỗi "flow" có thể là một dictionary mô tả nó.
        self.flow_table = [] 

        # Kho chứa thống kê từng port
        self.port_stats = {}

    def set_status(self, new_status):
        if new_status in ['up', 'unknown', 'offline', 'high-load']:
            self.status = new_status
            print(f"[{self.name}] Cập nhật trạng thái: {self.status}")
        else:
            print(f"[Lỗi] Trạng thái '{new_status}' không hợp lệ cho {self.name}.")

    def update_flow_table(self, new_flows):
        """
        Cập nhật toàn bộ bảng luồng cho switch.
        'new_flows' nên là một danh sách (list) các flow.
        """
        self.flow_table = new_flows
        print(f"[{self.name}] Đã cập nhật bảng luồng với {len(new_flows)} luồng.")

    def update_ports(self, port_list):
        self.port_list = port_list
        print(f"[{self.name}] Đã cập nhật cổng: {self.port_list}")
    
    def update_port_stats(self, stats_data, timestamp = None):
        """
        stats_data: Dictionary chứa thông tin các port từ Mininet gửi lên
        """
        if timestamp:
            self.last_update_time = datetime.fromtimestamp(timestamp)
        else:
            self.last_update_time = datetime.now()

        if self.status != 'up':
            self.set_status('up')

        self.port_list = list(stats_data.keys()) # cập nhập list port từ stat_data
        
        for port_name, stats in stats_data.items():
            stats['owner_switch'] = self.name
            stats['full_port_id'] = f"{self.name}:{port_name}"
            
        self.port_stats = stats_data
        

        total_dropped = sum(p['dropped'] for p in self.port_stats.values())
        if total_dropped > 100:
            print(f"[Cảnh báo] Switch {self.name} đang bị rớt gói: {total_dropped}")

    def heartbeat(self, timestamp = None):
        if timestamp:
            self.last_update_time = datetime.fromtimestamp(timestamp)
        else:
            self.last_update_time = datetime.now()

        if self.status in ['offline', 'unknown']:
            self.set_status('up')

        if self.status != 'up':
            self.set_status('up')

    def get_port_summary(self):
        """
        Trả về thông tin tóm tắt về các port
        """
        if not self.port_stats:
            return {"total_ports": 0, "active_ports": [], "total_traffic": 0}
            
        total_rx = sum(stats['rx_bytes'] for stats in self.port_stats.values())
        total_tx = sum(stats['tx_bytes'] for stats in self.port_stats.values())
        total_traffic = total_rx + total_tx
        
        return {
            "total_ports": len(self.port_stats),
            "active_ports": list(self.port_stats.keys()),
            "total_traffic_bytes": total_traffic,
            "total_traffic_mb": round(total_traffic / (1024*1024), 2)
        }

    def get_info(self):
        print("--- Thông tin Switch ---")
        print(f"  Tên    : {self.name}")
        print(f"  DPID   : {self.dpid}")
        print(f"  Trạng thái: {self.status}")
        print(f"  Cổng   : {', '.join(self.port_list)}")
        print(f"  Số luồng: {len(self.flow_table)}")
        print("------------------------")

    

    def to_json(self):
        active_ports = list(self.port_stats.keys()) if self.port_stats else self.port_list # cập nhập port mới nhất 
        
        return {
            'name': self.name,
            'dpid': self.dpid,
            'status': self.status,
            'ports': active_ports,
            'port_stats': self.port_stats,
            'flow_count': len(self.flow_table)
        }