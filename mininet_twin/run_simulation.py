import time
import sys
import random
import os
import socketio
import logging
import threading
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.link import TCLink
from topo import ConfigTopo
import collector
import link_collector
import requests

# --- CẤU HÌNH --- sua mot ti nef
API_BASE_URL = "http://localhost:5000/api"
SOCKET_URL = "http://localhost:5000"
SYNC_INTERVAL = 1.0  # 1 giây mỗi lần gửi

# ghi log

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)-8s] %(message)s',
    handlers=[
        logging.FileHandler("logs/mininet.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger()

# --- SOCKET.IO CLIENT ---
sio = socketio.Client()

@sio.event
def connect():
    logger.info("Đã kết nối WebSocket tới Backend!")

@sio.event
def connect_error(data):
    logger.error(f"Lỗi kết nối WebSocket: {data}")

@sio.event
def disconnect():
    logger.warning("Mất kết nối WebSocket!")


def push_topology_http(net):
    """Gửi cấu trúc mạng lên Backend qua HTTP"""
    logger.info(" Đang gửi topology lên Backend...")
    topology_data = { "hosts": [], "switches": [], "links": [] }
    for h in net.hosts:
        topology_data["hosts"].append({
            "name": h.name,
            "ip": h.IP(),
            "mac": h.MAC()
        })
    
    for s in net.switches:
        topology_data["switches"].append({
            "name": s.name,
            "dpid": s.dpid
        })
    
    processed = set() # để tránh 2 dây trùng nhau 
    for link in net.links:
        n1, n2 = link.intf1.node.name, link.intf2.node.name
        lid = "-".join(sorted([n1, n2]))
        if lid not in processed:
            processed.add(lid)
            topology_data["links"].append({
                "node1": n1,
                "node2": n2,
                "bandwidth": 100
            })

    try:
        response = requests.post(
            f"{API_BASE_URL}/init/topology",
            json=topology_data,
            timeout=5
        )
        response.raise_for_status()
        logger.info(f" Gửi Topology thành công: {len(net.hosts)} hosts, {len(net.switches)} switches")
        return True
    except Exception as e:
        logger.error(f" Lỗi gửi Topology: {e}")
        return False
    
# Tao luu luong
def generate_random_traffic(net):
    """
    Tạo traffic ngẫu nhiên để mô phỏng mạng thật đang hoạt động sôi nổi.
    """
    while True:
        try:
            #  Chọn ngẫu nhiên cặp Host (Src -> Dst)
            src, dst = random.sample(net.hosts, 2)
            
            #  Random băng thông
            bw_options = [5, 10, 20, 50, 80, 120] 
            bandwidth = random.choice(bw_options)
            
            # Random thời gian chạy 
            duration = random.randint(2, 5)
            
            logger.info(f" [Traffic] {src.name} -> {dst.name} : {bandwidth}Mbps trong {duration}s")
            
            #  Chạy lệnh iPerf (UDP)
            # -b: băng thông, -t: thời gian, -u: udp
            cmd = f'iperf -c {dst.IP()} -u -b {bandwidth}M -t {duration} &'
            src.cmd(cmd)
            
            #  Nghỉ một chút trước khi tạo luồng tiếp theo
            time.sleep(random.uniform(0.5, 2.0))
            
        except Exception as e:
            logger.error(f"Lỗi tạo traffic: {e}")
            time.sleep(1)

def start_traffic_simulation(net):
    # khởi động iPerf Server trên TẤT CẢ các host
    
    logger.info(" Khởi động iPerf Server trên toàn bộ Host...")
    for h in net.hosts:
        h.cmd('killall iperf 2>/dev/null')
        h.cmd('iperf -s -u &') # Chạy server nhận UDP
    
    # Chạy luồng tạo traffic ngẫu nhiên
    t = threading.Thread(target=generate_random_traffic, args=(net,), daemon=True)
    t.start()

def run_simulation():
    # Khởi tạo Mininet
    logger.info(" Khởi tạo mạng Mininet...")
    topo = ConfigTopo()
    # net = Mininet(topo=topo)
    net = Mininet(topo=topo, switch=OVSKernelSwitch, link=TCLink)
    net.start()
    
    logger.info(f" Mininet started with {len(net.hosts)} hosts, {len(net.switches)} switches")

    #  Kết nối WebSocket
    logger.info(f" Kết nối tới {SOCKET_URL}...")
    try:
        sio.connect(SOCKET_URL, wait_timeout=5)
    except Exception as e:
        logger.error(f" Không thể kết nối SocketIO: {e}")
        net.stop()
        return

    #  Gửi Topology
    if not push_topology_http(net):
        logger.error(" Không thể gửi topology, dừng chương trình")
        net.stop()
        return
    
    # Đợi Backend xử lý
    time.sleep(2)

    #  Khởi động iPerf Traffic
    logger.info(" Khởi động iPerf traffic...")
    if not start_traffic_simulation(net):
        logger.warning(" iPerf không khởi động được, nhưng tiếp tục chạy...")

    # 5. Main Loop - Thu thập và gửi dữ liệu
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
            current_time = time.time()
            real_interval = current_time - last_check_time
            last_check_time = current_time
            
            telemetry_batch = {
                "hosts": [],
                "links": [],
                "switches": []
            }

            #  Thu thập Host Metrics
            for h in net.hosts:
                cpu = collector.get_host_cpu_usage(h)
                mem = collector.get_host_memory_usage(h)
                telemetry_batch["hosts"].append({
                    "name": h.name,
                    "cpu": cpu,
                    "mem": mem
                })

            #  Thu thập Switch Metrics (Heartbeat)
            for s in net.switches:
                telemetry_batch["switches"].append(s.name)

            #  Thu thập Link Metrics
            link_stats = link_collector.collect_link_metrics(
                net,
                link_counters,
                real_interval
            )
            
            for lid, throughput in link_stats.items():
                telemetry_batch["links"].append({
                    "id": lid,
                    "bw": throughput
                })

            #  Tính toán thống kê
            total_bw = sum(d['bw'] for d in telemetry_batch['links'])
            avg_cpu = sum(h['cpu'] for h in telemetry_batch['hosts']) / len(net.hosts)
            
            #  Log thông tin
            logger.info(f"[Loop #{loop_count:04d}] Total BW: {total_bw:6.2f} Mbps | Avg CPU: {avg_cpu:5.1f}%")
            
            # Log chi tiết links có traffic
            active_links = [
                f"{l['id']}:{l['bw']:.1f}M"
                for l in telemetry_batch['links']
                if l['bw'] > 0.1
            ]
            if active_links:
                logger.info(f"   Active Links: {', '.join(active_links)}")
            else:
                logger.warning("    Không có link nào có traffic!")

            #  Gửi qua WebSocket
            try:
                sio.emit('mininet_telemetry', telemetry_batch)
            except Exception as e:
                logger.error(f" Lỗi gửi WebSocket: {e}")

            #  Sleep để giữ đúng interval
            elapsed = time.time() - start_time
            sleep_time = max(0.1, SYNC_INTERVAL - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        logger.info("\n Nhận Ctrl+C, đang dừng...")
    except Exception as e:
        logger.error(f"Lỗi nghiêm trọng: {e}", exc_info=True)
    finally:
        logger.info(" Dọn dẹp...")
        
        # Dừng iPerf
        for h in net.hosts:
            h.cmd('killall iperf 2>/dev/null')
        
        if sio.connected:
            sio.disconnect()
        
        net.stop()
        logger.info(" Đã dừng Mininet sạch sẽ")

if __name__ == '__main__':
    run_simulation()