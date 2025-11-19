
from datetime import datetime
class Link:

    THRESHOLD_WARNING = 70.0  # > 70% là cảnh báo (Cam)
    THRESHOLD_CRITICAL = 90.0 # > 90% là nguy hiểm (Đỏ)

    def __init__(self, node1, node2, bandwidth_capacity):
        """
            node1 (str): Tên của thiết bị 1 
            node2 (str): Tên của thiết bị 2 
            bandwidth_capacity (float): Băng thông tối đa (dung lượng)
                                        của link (tính bằng Mbps).
        """
        # Chúng ta tạo một ID duy nhất cho link để dễ dàng tham chiếu
        self.id = "-".join(sorted([node1, node2]))
        self.node1 = node1
        self.node2 = node2
        self.bandwidth_capacity = bandwidth_capacity  # (Mbps)

        
        self.status = 'unknown'  

        self.last_update_time = None
        
        # số liệu hiệu năng (performance metrics)
        # mà chúng ta muốn đồng bộ hóa từ Mininet ( dùng iPerf).
        self.current_throughput = 0.0  # (Mbps) - Băng thông đang sử dụng
        self.latency = 0.0             # (ms) - Độ trễ
        self.jitter = 0.0              # (ms) - Biến động độ trễ

    def set_status(self, new_status):
        # Thêm các trạng thái mới vào danh sách hợp lệ
        valid_states = ['up', 'down', 'unknown', 'warning', 'high-load']
        if new_status in valid_states:
            self.status = new_status
        

    def update_performance_metrics(self, throughput, latency=0.0, jitter=0.0):
        """
        Cập nhật các số liệu hiệu năng (dữ liệu từ iPerf!).
        """
        self.last_update_time = datetime.now()
        self.current_throughput = throughput
        self.latency = latency
        self.jitter = jitter
        
        # --- [LOGIC MỚI] Tự quyết định trạng thái tại đây ---
        utilization = self.get_utilization()
        
        if self.status != 'down': # Chỉ đánh giá nếu link không bị đứt
            if utilization >= self.THRESHOLD_CRITICAL:
                self.set_status('high-load')
            elif utilization >= self.THRESHOLD_WARNING:
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