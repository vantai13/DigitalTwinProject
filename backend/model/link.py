# class_link.py

class Link:
    """
    Một Lớp (Class) đại diện cho một liên kết (link) giữa hai thiết bị
    (ví dụ: Host-Switch, Switch-Switch).
    """
    
    def __init__(self, node1, node2, bandwidth_capacity):
        """
        Hàm khởi tạo cho Link.
        
        Args:
            node1 (str): Tên của thiết bị 1 (ví dụ: 'h1').
            node2 (str): Tên của thiết bị 2 (ví dụ: 's1').
            bandwidth_capacity (float): Băng thông tối đa (dung lượng)
                                        của link (tính bằng Mbps).
        """
        # --- 1. Thuộc tính Định danh (Identifier Attributes) ---
        # Chúng ta tạo một ID duy nhất cho link để dễ dàng tham chiếu
        self.id = f"{node1}-{node2}"
        self.node1 = node1
        self.node2 = node2
        self.bandwidth_capacity = bandwidth_capacity  # (Mbps)
        
        # --- 2. Thuộc tính Trạng thái (State Attributes) ---
        self.status = 'unknown'  # Trạng thái: 'up', 'down'
        
        # Đây là các số liệu hiệu năng (performance metrics)
        # mà chúng ta muốn đồng bộ hóa từ Mininet (ví dụ: dùng iPerf).
        self.current_throughput = 0.0  # (Mbps) - Băng thông đang sử dụng
        self.latency = 0.0             # (ms) - Độ trễ
        self.jitter = 0.0              # (ms) - Biến động độ trễ

    def set_status(self, new_status):
        """
        Cập nhật trạng thái 'up' hoặc 'down' của link.
        """
        if new_status in ['up', 'down', 'unknown']:
            self.status = new_status
            print(f"[{self.id}] Cập nhật trạng thái: {self.status}")
        else:
            print(f"[Lỗi] Trạng thái '{new_status}' không hợp lệ cho {self.id}.")

    def update_performance_metrics(self, throughput, latency=0.0, jitter=0.0):
        """
        Cập nhật các số liệu hiệu năng (đây là dữ liệu từ iPerf!).
        """
        self.current_throughput = throughput
        self.latency = latency
        self.jitter = jitter
        
        # Tính toán độ bão hòa (utilization) của link
        if self.bandwidth_capacity > 0:
            utilization = (self.current_throughput / self.bandwidth_capacity) * 100
            print(f"[{self.id}] Thông lượng: {self.current_throughput:.2f} Mbps "
                  f"(Sử dụng: {utilization:.2f}%)")
        else:
            print(f"[{self.id}] Thông lượng: {self.current_throughput:.2f} Mbps")

    def get_utilization(self):
        """
        Một phương thức tiện ích để tính toán % băng thông đang sử dụng.
        """
        if self.bandwidth_capacity == 0:
            return 0.0
        return (self.current_throughput / self.bandwidth_capacity) * 100

    def get_info(self):
        """
        In thông tin chi tiết của link ra.
        """
        print(f"--- Thông tin Link ({self.id}) ---")
        print(f"  Nối    : {self.node1} <--> {self.node2}")
        print(f"  Trạng thái: {self.status}")
        print(f"  Dung lượng: {self.bandwidth_capacity} Mbps")
        print(f"  Thông lượng: {self.current_throughput:.2f} Mbps")
        print(f"  Sử dụng  : {self.get_utilization():.2f} %")
        print(f"  Độ trễ   : {self.latency} ms")
        print("-------------------------------")

    def to_json(self):
        """
        Chuyển đổi thông tin của đối tượng Link thành một dictionary (JSON).
        """
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