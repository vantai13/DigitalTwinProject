class Host:

    HIGH_CPU_THRESHOLD = 90.0  # ngưỡng CPU cao (%)

    def __init__(self, name, ip_address, mac_address):
        """
            name (str): Tên của host
            ip_address (str): Địa chỉ IP của host.
            mac_address (str): Địa chỉ MAC của host
        """
       
        self.name = name
        self.ip_address = ip_address
        self.mac_address = mac_address
        
        # Đây là những thông tin động, sẽ được cập nhật liên tục từ Mininet.
        self.status = 'unknown'  # Trạng thái ban đầu
        
        # Thống kê tài nguyên (Resource metrics)
        self.cpu_utilization = 0.0  # (giá trị từ 0.0 đến 100.0)
        self.memory_usage = 0.0     # (giá trị từ 0.0 đến 100.0)
        
        # Thống kê mạng (Network metrics)
        self.tx_bytes = 0  # (Tổng số bytes đã gửi)
        self.rx_bytes = 0  # (Tổng số bytes đã nhận)

        

    def set_status(self, new_status):
        if new_status in ['up', 'unknown', 'offline', 'high-load']:
            self.status = new_status
            print(f"[{self.name}] Cập nhật trạng thái: {self.status}")
        else:
            print(f"[Lỗi] Trạng thái '{new_status}' không hợp lệ cho {self.name}.")

    def update_resource_metrics(self, cpu, memory):
        self.cpu_utilization = cpu
        self.memory_usage = memory

        if self.status != 'offline':
            
            if self.cpu_utilization >= self.HIGH_CPU_THRESHOLD:
                # Tự động gán 'high-load'
                # (Chỉ gán nếu trạng thái hiện tại chưa đúng)
                if self.status != 'high-load':
                    self.set_status('high-load')
            else:
                # Tự động quay về 'up' khi CPU giảm
                if self.status != 'up':
                    self.set_status('up')
        

    def update_network_metrics(self, tx_bytes, rx_bytes):
        self.tx_bytes = tx_bytes
        self.rx_bytes = rx_bytes

    def get_info(self):
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
        Chuyển đổi thông tin của đối tượng Host thành một dictionary.
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