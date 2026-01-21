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
# [MỚI] Import Command Executor
from controllers.command_executor import CommandExecutor

load_dotenv()


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
    topo = ConfigTopo() # Tạo một đối tường topology 
    net = Mininet(topo=topo, switch=OVSKernelSwitch, host=CPULimitedHost) # Khởi tạo mạng mininet
    net.start() # Khơi tạo mininet 
    logger.info(f" Mininet started with {len(net.hosts)} hosts, {len(net.switches)} switches")
   
   
   # tạo khóa 
    for h in net.hosts:
        h.lock = threading.Lock()

    for s in net.switches:
        s.lock = threading.Lock()

    # ========================================
    # ✅ FIX VẤN ĐỀ 3: KHỞI TẠO EXECUTOR TRƯỚC
    # ========================================
    command_executor = CommandExecutor(net)
    logger.info("✅ CommandExecutor initialized")

    # ✅ KHỞI TẠO SOCKET CLIENT VỚI EXECUTOR
    socket_client = SocketClient(SOCKET_URL, command_executor=command_executor)
    logger.info("✅ SocketClient initialized with CommandExecutor")

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

                # Kiểm tra xem interface có UP không
                intf_name = h.defaultIntf().name  # Thường là h1-eth0
                try:
                    if hasattr(h, 'lock'):
                        with h.lock:
                            # Chạy lệnh ip link show để kiểm tra status
                            intf_status = h.cmd(f'ip link show {intf_name}')
                    else:
                        intf_status = h.cmd(f'ip link show {intf_name}')
                    
                    # Kiểm tra xem interface có UP không
                    is_up = 'state UP' in intf_status
                    
                    if not is_up:
                        # Interface DOWN → Không thu thập metrics, gửi status offline
                        telemetry_batch["hosts"].append({
                            "name": h.name,
                            "cpu": 0.0,      # Force về 0
                            "mem": 0.0,      # Force về 0
                            "status": "offline"  # ← QUAN TRỌNG: Gửi status rõ ràng
                        })
                        logger.debug(f"[COLLECTOR] Host {h.name} interface DOWN, skip metrics")
                        continue  # Bỏ qua host này, chuyển sang host tiếp theo
                
                except Exception as e:
                    logger.warning(f"[COLLECTOR] Error checking {h.name} status: {e}")
                    # Nếu lỗi → Coi như offline
                    telemetry_batch["hosts"].append({
                        "name": h.name,
                        "cpu": 0.0,
                        "mem": 0.0,
                        "status": "offline"
                    })
                    continue

                # ========================================
                # CHỈ THU THẬP METRICS NẾU INTERFACE UP
                # ========================================

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
        logger.info("🧹 Dọn dẹp tài nguyên...")
        
        # ✅ FIX: CLEANUP TỪNG BƯỚC
        try:
            if traffic_gen:
                logger.info("  └─ Stopping traffic generator...")
                traffic_gen.stop()
        except Exception as e:
            logger.error(f"  └─ Error stopping traffic: {e}")
        
        try:
            logger.info("  └─ Stopping background measurement...")
            network_stats.stop_background_measurement()
        except Exception as e:
            logger.error(f"  └─ Error stopping measurement: {e}")
        
        try:
            if socket_client:
                logger.info("  └─ Disconnecting socket...")
                socket_client.disconnect()
        except Exception as e:
            logger.error(f"  └─ Error disconnecting socket: {e}")
        
        try:
            if net:
                logger.info("  └─ Stopping Mininet...")
                # ✅ QUAN TRỌNG: Kill all iPerf trước
                for h in net.hosts:
                    try:
                        h.cmd('killall -9 iperf 2>/dev/null')
                    except:
                        pass
                
                time.sleep(0.5)
                net.stop()
                logger.info("  └─ Mininet stopped successfully")
        except Exception as e:
            logger.error(f"  └─ Error stopping Mininet: {e}")
            # Force cleanup
            os.system('sudo mn -c 2>/dev/null')
        
        logger.info("✅ Cleanup hoàn tất")

if __name__ == '__main__':
    run_simulation()