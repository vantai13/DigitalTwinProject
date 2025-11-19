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
        # Chúng ta có thể lưu tên của các interface (ví dụ: 's1-eth1', 's1-eth2')
        self.port_list = []
        
        # Bảng luồng (Flow Table)
        # chúng ta chỉ lưu một danh sách các luồng (flows).
        # Mỗi "flow" có thể là một dictionary mô tả nó.
        self.flow_table = [] 

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

    def heartbeat(self):
        self.last_update_time = datetime.now()
        if self.status in ['offline', 'unknown']:
            self.set_status('up')

        if self.status != 'up':
            self.set_status('up')

    def get_info(self):
        print("--- Thông tin Switch ---")
        print(f"  Tên    : {self.name}")
        print(f"  DPID   : {self.dpid}")
        print(f"  Trạng thái: {self.status}")
        print(f"  Cổng   : {', '.join(self.port_list)}")
        print(f"  Số luồng: {len(self.flow_table)}")
        print("------------------------")

    

    def to_json(self):
        return {
            'name': self.name,
            'dpid': self.dpid,
            'status': self.status,
            'ports': self.port_list,
            'flow_count': len(self.flow_table)
        }