
from datetime import datetime
class Link:

    THRESHOLD_WARNING = 70.0  
    THRESHOLD_CRITICAL = 90.0 

    def __init__(self, node1, node2, bandwidth_capacity):
        """
            node1 (str): Tên của thiết bị 1 
            node2 (str): Tên của thiết bị 2 
            bandwidth_capacity (float): Băng thông tối đa (dung lượng)
                                        của link (tính bằng Mbps).
        """

        self.id = "-".join(sorted([node1, node2]))
        self.node1 = node1
        self.node2 = node2
        self.bandwidth_capacity = bandwidth_capacity  
        

        
        self.status = 'unknown'
        self.last_update_time = None
        
        self.current_throughput = 0.0  # (Mbps) - Băng thông đang sử dụng
        self.latency = 0.0             # (ms) - Độ trễ
        self.jitter = 0.0              # (ms) - Biến động độ trễ
        self.utilization = 0.0

    def set_status(self, new_status):
        valid_states = ['up', 'down', 'unknown', 'warning', 'high-load']
        if new_status in valid_states:
            self.status = new_status

        if self.status in ['down', 'unknown']:
            self.utilization = 0.0

        
    def update_performance_metrics(self, throughput, latency=0.0, jitter=0.0, timestamp = None):
        """
        Cập nhật các số liệu hiệu năng (dữ liệu từ iPerf!).
        """
        if timestamp: 
            self.last_update_time = datetime.fromtimestamp(timestamp)
        else: 
            self.last_update_time = datetime.now()

        self.current_throughput = throughput
        self.latency = latency
        self.jitter = jitter

        if throughput <= 0.01:  # Ngưỡng rất nhỏ để tránh lỗi làm tròn
            self.set_status('down')
            return
        
        
        self.utilization = self.get_utilization()
        
        if self.utilization >= self.THRESHOLD_CRITICAL:
            self.set_status('high-load')
        elif self.utilization >= self.THRESHOLD_WARNING:
            self.set_status('warning')
        else:
            self.set_status('up')

    def get_utilization(self):
        """
        tính toán % băng thông đang sử dụng.
        """
        if self.bandwidth_capacity == 0:
            return 0.0
        return (self.current_throughput / self.bandwidth_capacity) * 100

    def get_info(self):
        print(f"--- Thông tin Link ({self.id}) ---")
        print(f"  Nối    : {self.node1} <--> {self.node2}")
        print(f"  Trạng thái: {self.status}")
        print(f"  Dung lượng: {self.bandwidth_capacity} Mbps")
        print(f"  Thông lượng: {self.current_throughput:.2f} Mbps")
        print(f"  Sử dụng  : {self.get_utilization():.2f} %")
        print(f"  Độ trễ   : {self.latency} ms")
        print("-------------------------------")

    def to_json(self):
        return {
            'id': self.id,
            'node1': self.node1,
            'node2': self.node2,
            'status': self.status,
            'bandwidth_capacity': self.bandwidth_capacity,
            'current_throughput': self.current_throughput,
            'utilization': self.get_utilization(),
            'latency': self.latency,
            'jitter': self.jitter
        }