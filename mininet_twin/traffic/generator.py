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

                src, dst = random.sample(host_list, 2)

                # ✅ FIX: KIỂM TRA CẢ CARRIER STATUS
                src_intf_name = src.defaultIntf().name
                
                try:
                    if hasattr(src, 'lock'):
                        with src.lock:
                            src_status = src.cmd(f'ip link show {src_intf_name}')
                            # ✅ CHECK CARRIER
                            src_carrier = src.cmd(f'cat /sys/class/net/{src_intf_name}/carrier 2>/dev/null')
                    else:
                        src_status = src.cmd(f'ip link show {src_intf_name}')
                        src_carrier = src.cmd(f'cat /sys/class/net/{src_intf_name}/carrier 2>/dev/null')
                    
                    src_is_up = 'state UP' in src_status
                    src_has_carrier = '1' in src_carrier.strip()
                    
                    if not (src_is_up and src_has_carrier):
                        logger.debug(f"[TRAFFIC] {src.name} no carrier (UP:{src_is_up}, Carrier:{src_has_carrier})")
                        time.sleep(0.5)
                        continue
                
                except Exception as e:
                    logger.debug(f"[TRAFFIC] Error checking {src.name}: {e}")
                    time.sleep(0.5)
                    continue

                # TƯƠNG TỰ CHO DST
                dst_intf_name = dst.defaultIntf().name
                
                try:
                    if hasattr(dst, 'lock'):
                        with dst.lock:
                            dst_status = dst.cmd(f'ip link show {dst_intf_name}')
                            dst_carrier = dst.cmd(f'cat /sys/class/net/{dst_intf_name}/carrier 2>/dev/null')
                    else:
                        dst_status = dst.cmd(f'ip link show {dst_intf_name}')
                        dst_carrier = dst.cmd(f'cat /sys/class/net/{dst_intf_name}/carrier 2>/dev/null')
                    
                    dst_is_up = 'state UP' in dst_status
                    dst_has_carrier = '1' in dst_carrier.strip()
                    
                    if not (dst_is_up and dst_has_carrier):
                        logger.debug(f"[TRAFFIC] {dst.name} no carrier (UP:{dst_is_up}, Carrier:{dst_has_carrier})")
                        time.sleep(0.5)
                        continue
                
                except Exception as e:
                    logger.debug(f"[TRAFFIC] Error checking {dst.name}: {e}")
                    time.sleep(0.5)
                    continue
                
                # CHỈ GỬI TRAFFIC NẾU CẢ 2 ĐỀU CÓ CARRIER
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