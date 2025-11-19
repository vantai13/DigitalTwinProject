# mininet_twin/main.py
import time
import sys
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.link import TCLink

# Import các module đã tách
from core.topo import ConfigTopo
from services.api_client import push_topology
from services.socket_client import SocketClient
from traffic.generator import TrafficGenerator
from collectors import host_stats, link_stats
import config
from utils.logger import logger

def main():
    logger.info("=== KHỞI ĐỘNG MININET DIGITAL TWIN ===")
    
    # 1. Khởi tạo mạng
    topo = ConfigTopo()
    net = Mininet(topo=topo, switch=OVSKernelSwitch)
    net.start()
    logger.info(f"Mạng đã chạy: {len(net.hosts)} hosts, {len(net.switches)} switches")

    # 2. Kết nối SocketIO & Gửi Topology
    socket_client = SocketClient()
    if not socket_client.connect():
        logger.error("Không thể kết nối SocketIO. Dừng chương trình.")
        net.stop()
        return

    if not push_topology(net):
        logger.error("Không thể gửi topology qua API. Dừng chương trình.")
        net.stop()
        return

    # 3. Khởi động Traffic (iPerf)
    traffic_gen = TrafficGenerator(net)
    traffic_gen.start()

    # 4. Vòng lặp thu thập dữ liệu (Giống logic cũ)
    link_counters = {} # Lưu bytes cũ để tính delta
    loop_count = 0
    last_check_time = time.time()

    try:
        while True:
            loop_count += 1
            start_time = time.time()
            
            # Tính interval thực tế (quan trọng để tính Mbps chính xác)
            current_time = time.time()
            real_interval = current_time - last_check_time
            last_check_time = current_time
            if real_interval <= 0: real_interval = 0.1

            # --- THU THẬP DỮ LIỆU ---
            batch_data = {
                "hosts": [],
                "links": [],
                "switches": []
            }

            # A. Hosts Stats
            for h in net.hosts:
                batch_data["hosts"].append({
                    "name": h.name,
                    "cpu": host_stats.get_host_cpu_usage(h),
                    "mem": host_stats.get_host_memory_usage(h)
                })

            # B. Switches (Heartbeat)
            for s in net.switches:
                batch_data["switches"].append(s.name)

            # C. Links Stats (Logic phức tạp nằm ở đây)
            throughput_map = link_stats.collect_link_metrics(net, link_counters, real_interval)
            
            for lid, bw in throughput_map.items():
                batch_data["links"].append({
                    "id": lid,
                    "bw": bw
                })

            # --- LOGGING ---
            total_bw = sum(l['bw'] for l in batch_data['links'])
            logger.info(f"[Loop #{loop_count}] Total BW: {total_bw:.2f} Mbps")

            # --- GỬI SOCKET ---
            socket_client.send_telemetry(batch_data)

            # Sleep bù trừ thời gian xử lý để đảm bảo interval ổn định
            elapsed = time.time() - start_time
            sleep_time = max(0.1, config.SYNC_INTERVAL - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        logger.info("\nĐang dừng hệ thống...")
    finally:
        traffic_gen.stop()
        socket_client.close()
        net.stop()
        logger.info("Đã tắt hoàn toàn.")

if __name__ == '__main__':
    main()