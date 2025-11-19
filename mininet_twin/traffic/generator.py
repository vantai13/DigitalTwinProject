# mininet_twin/traffic/generator.py
import threading
import random
import time
from utils.logger import logger

class TrafficGenerator:
    def __init__(self, net):
        self.net = net
        self.running = False
        self.bw_options = [5, 10, 20, 50, 80, 120] # Mbps options

    def _start_servers(self):
        logger.info("Khởi động iPerf Server trên toàn bộ Host...")
        for h in self.net.hosts:
            h.cmd('killall iperf 2>/dev/null')
            h.cmd('iperf -s -u &') # Chạy mode UDP Server

    def _generate_loop(self):
        logger.info("Bắt đầu luồng tạo traffic ngẫu nhiên...")
        while self.running:
            try:
                if len(self.net.hosts) < 2: continue

                src, dst = random.sample(self.net.hosts, 2)
                bw = random.choice(self.bw_options)
                duration = random.randint(2, 5)
                
                # Log nhẹ để biết có traffic
                # logger.info(f"[Traffic] {src.name} -> {dst.name}: {bw}M ({duration}s)")
                
                # Lệnh iperf client
                cmd = f'iperf -c {dst.IP()} -u -b {bw}M -t {duration} &'
                src.cmd(cmd)
                
                time.sleep(random.uniform(0.5, 2.0))
            except Exception as e:
                logger.error(f"Lỗi traffic: {e}")
                time.sleep(1)

    def start(self):
        if self.running: return
        self.running = True
        self._start_servers()
        # Chạy loop trong thread riêng
        t = threading.Thread(target=self._generate_loop, daemon=True)
        t.start()

    def stop(self):
        self.running = False
        logger.info("Đang dừng Traffic Generator...")
        for h in self.net.hosts:
            h.cmd('killall iperf 2>/dev/null')