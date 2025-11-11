# class_switch.py

class Switch:
    """
    Một Lớp (Class) đại diện cho một Switch ảo trong mạng.
    Đây là "bản sao số" của một switch (thường là Open vSwitch) trong Mininet.
    """
    
    def __init__(self, name, dpid):
        """
        Hàm khởi tạo cho Switch.
        
        Args:
            name (str): Tên của switch (ví dụ: 's1', 's2').
            dpid (str): Datapath ID. Đây là một định danh duy nhất
                        của Open vSwitch, rất quan trọng để điều khiển.
                        (Ví dụ: '0000000000000001')
        """
        # --- 1. Thuộc tính Định danh (Identifier Attributes) ---
        self.name = name
        self.dpid = dpid
        
        # --- 2. Thuộc tính Trạng thái (State Attributes) ---
        self.status = 'unknown'  # Trạng thái: 'up', 'down'
        
        # Danh sách các cổng (ports) mà switch này đang kết nối
        # Chúng ta có thể lưu tên của các interface (ví dụ: 's1-eth1', 's1-eth2')
        self.port_list = []
        
        # Bảng luồng (Flow Table)
        # Đây là phần phức tạp nhất để "sao chép".
        # Ở mức độ đơn giản, chúng ta chỉ lưu một danh sách các luồng (flows).
        # Mỗi "flow" có thể là một dictionary mô tả nó.
        self.flow_table = [] 

    def set_status(self, new_status):
        """
        Cập nhật trạng thái 'up' hoặc 'down' của switch.
        """
        if new_status in ['up', 'down', 'unknown']:
            self.status = new_status
            print(f"[{self.name}] Cập nhật trạng thái: {self.status}")
        else:
            print(f"[Lỗi] Trạng thái '{new_status}' không hợp lệ cho {self.name}.")

    def update_flow_table(self, new_flows):
        """
        Cập nhật toàn bộ bảng luồng cho switch này.
        'new_flows' nên là một danh sách (list) các flow.
        """
        # Đây là một mô hình đơn giản. Trong thực tế, bạn sẽ nhận
        # dữ liệu này từ một bộ điều khiển (Controller) như Ryu hoặc POX.
        self.flow_table = new_flows
        print(f"[{self.name}] Đã cập nhật bảng luồng với {len(new_flows)} luồng.")

    def update_ports(self, port_list):
        """
        Cập nhật danh sách các cổng đang hoạt động.
        """
        self.port_list = port_list
        print(f"[{self.name}] Đã cập nhật cổng: {self.port_list}")

    def get_info(self):
        """
        In thông tin chi tiết của switch ra.
        """
        print("--- Thông tin Switch ---")
        print(f"  Tên    : {self.name}")
        print(f"  DPID   : {self.dpid}")
        print(f"  Trạng thái: {self.status}")
        print(f"  Cổng   : {', '.join(self.port_list)}")
        print(f"  Số luồng: {len(self.flow_table)}")
        # In chi tiết các luồng nếu cần (có thể rất dài)
        # for i, flow in enumerate(self.flow_table):
        #     print(f"    Flow {i}: {flow}")
        print("------------------------")

    def to_json(self):
        """
        Chuyển đổi thông tin của đối tượng Switch thành một dictionary (JSON).
        """
        return {
            'name': self.name,
            'dpid': self.dpid,
            'status': self.status,
            'ports': self.port_list,
            'flow_count': len(self.flow_table),
            # Gửi toàn bộ bảng luồng có thể làm JSON rất lớn,
            # nên chúng ta có thể chỉ gửi số lượng hoặc một bản tóm tắt.
            # 'flow_table': self.flow_table 
        }