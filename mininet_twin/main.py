import time
import sys
import threading
import os

from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch, CPULimitedHost
from mininet.link import TCLink


from utils.logger import setup_logger
from core.topo import ConfigTopo
from collectors import host_stats
from collectors import link_stats
from collectors import network_stats
from collectors import switch_stats
from services.api_client import TopologyApiClient
from services.socket_client import SocketClient
from traffic.generator import TrafficGenerator
from dotenv import load_dotenv


# Load .env
load_dotenv()

# Constants from .env
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5000/api')
SOCKET_URL = os.getenv('SOCKET_URL', 'http://localhost:5000')
SYNC_INTERVAL = float(os.getenv('SYNC_INTERVAL', 1.0))
TRAFFIC_ENABLED = os.getenv('TRAFFIC_GENERATION_ENABLED', 'true').lower() == 'true'

# Khởi tạo Logger
logger = setup_logger()

# Khởi tạo Clients
api_client = TopologyApiClient(API_BASE_URL)
socket_client = SocketClient(SOCKET_URL)

def run_simulation():
    #  Khởi tạo Mininet
    logger.info(" Khởi tạo mạng Mininet...")
    topo = ConfigTopo()
    net = Mininet(topo=topo, switch=OVSKernelSwitch, host=CPULimitedHost)
    net.start()
    logger.info(f" Mininet started with {len(net.hosts)} hosts, {len(net.switches)} switches")
   
   # tạo khóa 
    for h in net.hosts:
        h.lock = threading.Lock()

    #  Khởi tạo Traffic Generator
    traffic_gen = TrafficGenerator(net)

    #  Kết nối WebSocket
    if not socket_client.connect():
        net.stop()
        return

    #  Gửi Topology
    if not api_client.push_topology(net):
        logger.error(" Không thể gửi topology, dừng chương trình")
        net.stop()
        return
    
    time.sleep(2) # Đợi backend xử lý

    #  Bắt đầu sinh Traffic
    traffic_gen.start()

    network_stats.start_background_measurement(net)

    logger.info("Đang làm nóng hệ thống (Warm-up 3s) để thu thập metrics đầu tiên...")
    time.sleep(3.0) 

    #  Vòng lặp chính (Thu thập & Gửi dữ liệu)
    logger.info("=" * 70)
    logger.info(" BẮT ĐẦU VÒNG LẶP THU THẬP DỮ LIỆU")
    logger.info("=" * 70)
    
    link_counters = {}
    # [THAY ĐỔI] Tạo từ điển lưu throughput cũ
    link_throughput_tracker = {}
    loop_count = 0
    last_check_time = time.monotonic()
    try:
        while True:
            loop_count += 1
            loop_start_time = time.monotonic() 
            
            # Tính thời gian thực trôi qua
            current_time = time.monotonic()
            real_interval = current_time - last_check_time # tính thời gian chênh lệch giữa 2 vòng lặp đẻ tính bằng thoong
            
            # Tránh lỗi chia cho 0 hoặc số âm quá nhỏ
            if real_interval < 0.001: 
                real_interval = 0.001
                
            last_check_time = current_time
            
            current_timestamp = time.time()

            telemetry_batch = {
                "timestamp": current_timestamp,
                "hosts": [],
                "links": [],
                "switches": [],
                "latency": []
            }

            
            # Host Metrics
            for h in net.hosts:
                telemetry_batch["hosts"].append({
                    "name": h.name,
                    "cpu": host_stats.get_host_cpu_usage(h),
                    "mem": host_stats.get_host_memory_usage(h)
                })

            # Switch Metrics (Heartbeat)
            switch_data_collected = switch_stats.collect_switch_port_stats(net)
            

            telemetry_batch["switches"] = [] 
            for sw in net.switches:
                s_name = sw.name
                s_stats = switch_data_collected.get(s_name, {})
                
                telemetry_batch["switches"].append({
                    "name": s_name,
                    "ports": s_stats 
                })

            

            # Link Metrics
            current_link_metrics = link_stats.collect_link_metrics(
                net, link_counters, link_throughput_tracker, real_interval
            )
            for lid, throughput in current_link_metrics.items():
                telemetry_batch["links"].append({"id": lid, "bw": throughput})

           
           # Latency & Loss Metrics
            path_data = network_stats.measure_path_metrics(net)

            for pair_id, metrics in path_data.items():
                telemetry_batch["latency"].append({
                    "pair": pair_id,
                    "latency": metrics['latency'],
                    "loss": metrics['loss'],
                    "jitter": metrics['jitter']      
                })

            # --- Log & Gửi dữ liệu ---
            
            total_bw = sum(d['bw'] for d in telemetry_batch['links'])
            avg_cpu = 0
            if telemetry_batch['hosts']:
                avg_cpu = sum(h['cpu'] for h in telemetry_batch['hosts']) / len(telemetry_batch['hosts'])

            logger.info(f"[Loop #{loop_count:04d}] Total BW: {total_bw:6.2f} Mbps | Avg CPU: {avg_cpu:5.1f}%")
            
            socket_client.send_telemetry(telemetry_batch)

            # Sleep giữ nhịp
            elapsed = time.monotonic() - loop_start_time
            sleep_time = max(0.1, SYNC_INTERVAL - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        logger.info("\n Nhận Ctrl+C, đang dừng...")
    except Exception as e:
        logger.error(f"Lỗi nghiêm trọng: {e}", exc_info=True)
    finally:
        logger.info(" Dọn dẹp tài nguyên...")
        
        network_stats.stop_background_measurement()
        traffic_gen.stop()       # Dừng traffic
        socket_client.disconnect() # Ngắt kết nối socket
        net.stop()               # Dừng Mininet
        
        logger.info(" Đã dừng Mininet sạch sẽ")

if __name__ == '__main__':
    run_simulation()