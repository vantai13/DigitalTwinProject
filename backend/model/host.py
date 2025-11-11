# class_host.py

class Host:
    """
    Một Lớp (Class) đại diện cho một Host ảo trong mạng.
    Đây là "bản sao số" của một host trong Mininet.
    """
    
    def __init__(self, name, ip_address, mac_address):
        """
        Đây là hàm khởi tạo (constructor).
        Nó được gọi tự động khi một đối tượng Host mới được tạo ra.
        
        Args:
            name (str): Tên của host (ví dụ: 'h1', 'h2').
            ip_address (str): Địa chỉ IP của host (ví dụ: '10.0.0.1').
            mac_address (str): Địa chỉ MAC của host (ví dụ: '00:00:00:00:00:01').
        """
        # --- 1. Thuộc tính Định danh (Identifier Attributes) ---
        # Đây là những thông tin tĩnh, thường không thay đổi.
        self.name = name
        self.ip_address = ip_address
        self.mac_address = mac_address
        
        # --- 2. Thuộc tính Trạng thái (State Attributes) ---
        # Đây là những thông tin động, sẽ được cập nhật liên tục từ Mininet.
        self.status = 'unknown'  # Trạng thái ban đầu, ví dụ: 'up', 'down', 'unknown'
        
        # Thống kê tài nguyên (Resource metrics)
        self.cpu_utilization = 0.0  # (giá trị từ 0.0 đến 100.0)
        self.memory_usage = 0.0     # (giá trị từ 0.0 đến 100.0)
        
        # Thống kê mạng (Network metrics)
        # Chúng ta có thể lưu trữ thông tin về lưu lượng mà host này đang gửi/nhận
        self.tx_bytes = 0  # (Tổng số bytes đã gửi)
        self.rx_bytes = 0  # (Tổng số bytes đã nhận)

    def set_status(self, new_status):
        """
        Một phương thức (method) để cập nhật trạng thái của host.
        Ví dụ: 'up' hoặc 'down'.
        """
        if new_status in ['up', 'down', 'unknown']:
            self.status = new_status
            print(f"[{self.name}] Cập nhật trạng thái: {self.status}")
        else:
            print(f"[Lỗi] Trạng thái '{new_status}' không hợp lệ cho {self.name}.")

    def update_resource_metrics(self, cpu, memory):
        """
        Một phương thức để cập nhật số liệu tài nguyên (CPU, Memory).
        """
        self.cpu_utilization = cpu
        self.memory_usage = memory

    def update_network_metrics(self, tx_bytes, rx_bytes):
        """
        Một phương thức để cập nhật số liệu mạng (TX/RX).
        """
        self.tx_bytes = tx_bytes
        self.rx_bytes = rx_bytes

    def get_info(self):
        """
        Một phương thức tiện ích để "in" thông tin của host ra.
        Rất hữu dụng để kiểm tra (debug).
        """
        print("--- Thông tin Host ---")
        print(f"  Tên    : {self.name}")
        print(f"  IP     : {self.ip_address}")
        print(f"  MAC    : {self.mac_address}")
        print(f"  Trạng thái: {self.status}")
        print(f"  CPU    : {self.cpu_utilization}%")
        print(f"  Memory : {self.memory_usage}%")
        print(f"  TX Bytes: {self.tx_bytes}")
        print(f"  RX Bytes: {self.rx_bytes}")
        print("-----------------------")

    def to_json(self):
        """
        Chuyển đổi thông tin của đối tượng Host thành một dictionary,
        để dễ dàng gửi qua API (JSON).
        """
        return {
            'name': self.name,
            'ip_address': self.ip_address,
            'mac_address': self.mac_address,
            'status': self.status,
            'cpu_utilization': self.cpu_utilization,
            'memory_usage': self.memory_usage,
            'tx_bytes': self.tx_bytes,
            'rx_bytes': self.rx_bytes
        }