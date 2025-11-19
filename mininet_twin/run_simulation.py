import time
import sys

from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.link import TCLink

# --- IMPORTS CÁC MODULE ĐÃ TÁCH ---
from utils.logger import setup_logger
from core.topo import ConfigTopo
from collectors import host_stats
from collectors import link_stats
from services.api_client import TopologyApiClient
from services.socket_client import SocketClient
from traffic.generator import TrafficGenerator

# --- CẤU HÌNH ---
API_BASE_URL = "http://localhost:5000/api"
SOCKET_URL = "http://localhost:5000"
SYNC_INTERVAL = 1.0 

# Khởi tạo Logger
logger = setup_logger()

# Khởi tạo Clients
api_client = TopologyApiClient(API_BASE_URL)
socket_client = SocketClient(SOCKET_URL)

def run_simulation():
    # 1. Khởi tạo Mininet
    logger.info(" Khởi tạo mạng Mininet...")
    topo = ConfigTopo()
    net = Mininet(topo=topo, switch=OVSKernelSwitch, link=TCLink)
    net.start()
    logger.info(f" Mininet started with {len(net.hosts)} hosts, {len(net.switches)} switches")

    # 2. Khởi tạo Traffic Generator
    traffic_gen = TrafficGenerator(net)

    # 3. Kết nối WebSocket
    if not socket_client.connect():
        net.stop()
        return

    # 4. Gửi Topology
    if not api_client.push_topology(net):
        logger.error(" Không thể gửi topology, dừng chương trình")
        net.stop()
        return
    
    time.sleep(2) # Đợi backend xử lý

    # 5. Bắt đầu sinh Traffic
    traffic_gen.start()

    # 6. Vòng lặp chính (Thu thập & Gửi dữ liệu)
    logger.info("=" * 70)
    logger.info(" BẮT ĐẦU VÒNG LẶP THU THẬP DỮ LIỆU")
    logger.info("=" * 70)
    
    link_counters = {}
    loop_count = 0
    last_check_time = time.time()

    try:
        while True:
            loop_count += 1
            start_time = time.time()
            
            # Tính thời gian thực giữa các lần đo để tính băng thông chính xác
            current_time = time.time()
            real_interval = current_time - last_check_time
            last_check_time = current_time
            
            telemetry_batch = {
                "hosts": [],
                "links": [],
                "switches": []
            }

            # --- Thu thập Metrics ---
            
            # Host Metrics
            for h in net.hosts:
                telemetry_batch["hosts"].append({
                    "name": h.name,
                    "cpu": host_stats.get_host_cpu_usage(h),
                    "mem": host_stats.get_host_memory_usage(h)
                })

            # Switch Metrics (Heartbeat)
            for s in net.switches:
                telemetry_batch["switches"].append(s.name)

            # Link Metrics
            current_link_metrics = link_stats.collect_link_metrics(
                net, link_counters, real_interval
            )
            for lid, throughput in current_link_metrics.items():
                telemetry_batch["links"].append({"id": lid, "bw": throughput})

            # --- Log & Gửi dữ liệu ---
            
            total_bw = sum(d['bw'] for d in telemetry_batch['links'])
            avg_cpu = 0
            if telemetry_batch['hosts']:
                avg_cpu = sum(h['cpu'] for h in telemetry_batch['hosts']) / len(telemetry_batch['hosts'])

            logger.info(f"[Loop #{loop_count:04d}] Total BW: {total_bw:6.2f} Mbps | Avg CPU: {avg_cpu:5.1f}%")
            
            socket_client.send_telemetry(telemetry_batch)

            # --- Sleep giữ nhịp ---
            elapsed = time.time() - start_time
            sleep_time = max(0.1, SYNC_INTERVAL - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        logger.info("\n Nhận Ctrl+C, đang dừng...")
    except Exception as e:
        logger.error(f"Lỗi nghiêm trọng: {e}", exc_info=True)
    finally:
        logger.info(" Dọn dẹp tài nguyên...")
        
        traffic_gen.stop()       # Dừng traffic
        socket_client.disconnect() # Ngắt kết nối socket
        net.stop()               # Dừng Mininet
        
        logger.info(" Đã dừng Mininet sạch sẽ")

if __name__ == '__main__':
    run_simulation()