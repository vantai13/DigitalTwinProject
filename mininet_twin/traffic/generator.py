import time
import random
import threading
from utils.logger import setup_logger

logger = setup_logger()

class TrafficGenerator:
    def __init__(self, net):
        """
        Khởi tạo bộ sinh lưu lượng.
        """
        self.net = net
        self.running = False
        self.thread = None

    def _start_servers(self):
        """Khởi động iPerf Server trên tất cả các Host để sẵn sàng nhận gói tin."""
        logger.info(" Khởi động iPerf Server trên toàn bộ Host...")
        for h in self.net.hosts:
            # Kill process cũ nếu có
            h.cmd('killall iperf 2>/dev/null')
            # Chạy server ở chế độ UDP (-u), background (&)
            h.cmd('iperf -s -u &')

    def _traffic_loop(self):
        """Vòng lặp chính để sinh traffic ngẫu nhiên."""
        logger.info(" Bắt đầu vòng lặp sinh traffic ngẫu nhiên...")
        
        while self.running:
            try:
                # Chọn ngẫu nhiên cặp Host (Src -> Dst)
                src, dst = random.sample(self.net.hosts, 2)
                
                # Random băng thông và thời gian
                bw_options = [5, 10, 20, 50, 80, 120] 
                bandwidth = random.choice(bw_options)
                duration = random.randint(2, 5)
                
                logger.info(f" [Traffic] {src.name} -> {dst.name} : {bandwidth}Mbps trong {duration}s")
                
                # Gửi lệnh tạo traffic (Client -> Server)
                cmd = f'iperf -c {dst.IP()} -u -b {bandwidth}M -t {duration} &'
                src.cmd(cmd)
                
                # Nghỉ ngẫu nhiên trước khi tạo luồng tiếp theo
                time.sleep(random.uniform(0.5, 2.0))
                
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp traffic: {e}")
                time.sleep(1)

    def start(self):
        """Bắt đầu quy trình sinh traffic."""
        if self.running:
            logger.warning(" Traffic Generator đang chạy rồi!")
            return

        self._start_servers()
        self.running = True
        
        # Chạy vòng lặp sinh traffic trong một luồng riêng biệt (Daemon Thread)
        self.thread = threading.Thread(target=self._traffic_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Dừng sinh traffic và dọn dẹp các tiến trình iperf."""
        logger.info(" Đang dừng Traffic Generator...")
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
            
        # Dọn dẹp các tiến trình iperf còn sót lại
        for h in self.net.hosts:
            h.cmd('killall iperf 2>/dev/null')
        
        logger.info(" Đã dọn dẹp iPerf.")