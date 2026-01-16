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
        logger.info("🔄 Bắt đầu vòng lặp sinh traffic ngẫu nhiên...")
        
        while self.running:
            try:
                host_list = list(self.net.hosts)
                if len(host_list) < 2:
                    time.sleep(1)
                    continue

                # Chọn ngẫu nhiên cặp Host
                src, dst = random.sample(host_list, 2)

                # ========================================
                # KIỂM TRA SRC INTERFACE (QUAN TRỌNG!)
                # ========================================
                src_intf_name = src.defaultIntf().name
                
                try:
                    if hasattr(src, 'lock'):
                        with src.lock:
                            src_status = src.cmd(f'ip link show {src_intf_name}')
                    else:
                        src_status = src.cmd(f'ip link show {src_intf_name}')
                    
                    src_is_up = 'state UP' in src_status
                    
                    if not src_is_up:
                        logger.debug(f"[TRAFFIC] Source {src.name} offline, skip")
                        time.sleep(0.5)
                        continue
                
                except Exception as e:
                    logger.debug(f"[TRAFFIC] Error checking {src.name}: {e}")
                    time.sleep(0.5)
                    continue

                # ========================================
                # KIỂM TRA DST INTERFACE (ĐÃ CÓ)
                # ========================================
                dst_intf_name = dst.defaultIntf().name
                
                try:
                    if hasattr(dst, 'lock'):
                        with dst.lock:
                            dst_status = dst.cmd(f'ip link show {dst_intf_name}')
                    else:
                        dst_status = dst.cmd(f'ip link show {dst_intf_name}')
                    
                    dst_is_up = 'state UP' in dst_status
                    
                    if not dst_is_up:
                        logger.debug(f"[TRAFFIC] Destination {dst.name} offline, skip")
                        time.sleep(0.5)
                        continue
                
                except Exception as e:
                    logger.debug(f"[TRAFFIC] Error checking {dst.name}: {e}")
                    time.sleep(0.5)
                    continue
                
                # ========================================
                # CHỈ GỬI TRAFFIC NẾU CẢ 2 ĐỀU UP
                # ========================================
                bw_options = [5, 10, 20, 50, 80, 120]
                bandwidth = random.choice(bw_options)
                duration = random.randint(2, 5)
                
                cmd = f'iperf -c {dst.IP()} -u -b {bandwidth}M -t {duration} &'
                
                try:
                    if hasattr(src, 'lock'):
                        with src.lock:
                            if src.shell and not getattr(src, 'waiting', False):
                                src.cmd(cmd)
                    else:
                        if src.shell and not getattr(src, 'waiting', False):
                            src.cmd(cmd)
                
                except Exception as e:
                    logger.error(f"[TRAFFIC] Error sending: {e}")
                
                time.sleep(random.uniform(0.5, 2.0))
            
            except Exception as e:
                logger.error(f"[TRAFFIC] Loop error: {e}")
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
            self.thread.join(timeout=2.0)
            
        # Dọn dẹp các tiến trình iperf còn sót lại
        for h in self.net.hosts:
            try:
                if hasattr(h, 'shell') and h.shell:
                    h.cmd('killall iperf 2>/dev/null')
            except Exception as e:
                logger.warning(f"Không thể dọn dẹp iperf trên {h.name}: {e}")
        
        logger.info(" Đãf dọn dẹp iPer.")