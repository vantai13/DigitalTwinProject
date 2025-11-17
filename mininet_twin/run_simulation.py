import time
import sys
import os
import socketio
import logging
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from topo import ConfigTopo
import collector
import link_collector
import requests

# --- CẤU HÌNH ---
API_BASE_URL = "http://localhost:5000/api"
SOCKET_URL = "http://localhost:5000"
SYNC_INTERVAL = 1.0  # Tăng nhẹ lên 1s để dễ nhìn log (0.5s hơi nhanh quá nếu debug)

# --- LOGGING ---
# Định dạng log rõ ràng hơn
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger()

# --- SOCKET.IO CLIENT ---
sio = socketio.Client()

@sio.event
def connect():
    logger.info("Đã kết nối WebSocket tới Backend thành công!")

@sio.event
def connect_error(data):
    logger.error(f" Lỗi kết nối WebSocket: {data}")

@sio.event
def disconnect():
    logger.warning(" Mất kết nối WebSocket!")

def push_topology_http(net):
    logger.info(" Đang gửi cấu trúc mạng (Topology) lên Backend...")
    topology_data = { "hosts": [], "switches": [], "links": [] }

    for h in net.hosts:
        topology_data["hosts"].append({"name": h.name, "ip": h.IP(), "mac": h.MAC()})
    
    for s in net.switches:
        topology_data["switches"].append({"name": s.name, "dpid": s.dpid})
    
    processed = set()
    for link in net.links:
        n1, n2 = link.intf1.node.name, link.intf2.node.name
        lid = "-".join(sorted([n1, n2]))
        if lid not in processed:
            processed.add(lid)
            topology_data["links"].append({"node1": n1, "node2": n2, "bandwidth": 100})

    try:
        requests.post(f"{API_BASE_URL}/init/topology", json=topology_data, timeout=5)
        logger.info(f" Gửi Topology thành công: {len(net.hosts)} hosts, {len(net.switches)} switches")
        return True
    except Exception as e:
        logger.error(f" Lỗi gửi Topology: {e}")
        return False

def run_simulation():
    # 1. Khởi tạo Mininet
    logger.info("🛠️ Đang khởi tạo mạng Mininet...")
    topo = ConfigTopo()
    net = Mininet(topo=topo)
    net.start()

    # 2. Kết nối WebSocket
    logger.info(f"🔌 Đang kết nối tới {SOCKET_URL}...")
    try:
        sio.connect(SOCKET_URL)
    except Exception as e:
        logger.error(f" Không thể kết nối SocketIO: {e}")
        net.stop()
        return

    # 3. Gửi Topology
    if not push_topology_http(net):
        net.stop()
        return

    # 4. KHỞI ĐỘNG IPERF (Đã sửa lỗi logic)
    if len(net.hosts) >= 2:
        server = net.hosts[-1] # Host cuối làm Server
        clients = net.hosts[:-1] # Các host còn lại làm Client
        
        server_ip = server.IP()
        logger.info(f" [iPerf] Khởi động Server trên {server.name} ({server_ip})...")
        
        # Chạy Server
        server.cmd('iperf -s -u &')
        
        # QUAN TRỌNG: Đợi 2 giây để Server sẵn sàng nhận kết nối
        logger.info(" Đợi 2s để iPerf Server sẵn sàng...")
        time.sleep(2)

        # Chạy Client
        for client in clients:
            logger.info(f" [iPerf] {client.name} bắt đầu bắn dữ liệu tới {server.name}...")
            # Chạy vô hạn (-t 999999), băng thông 5M (-b 5M)
            client.cmd(f'iperf -c {server_ip} -u -b 5M -t 999999 &')
    else:
        logger.warning(" Không đủ host để chạy kịch bản iPerf!")

    logger.info(">>> Bắt đầu vòng lặp thu thập dữ liệu (Real-time)...")
    
    link_counters = {} 

    try:
        while True:
            start_time = time.time()
            
            telemetry_batch = {
                "hosts": [],
                "links": [],
                "switches": []
            }

            # A. Host Metrics
            for h in net.hosts:
                cpu = collector.get_host_cpu_usage(h)
                mem = collector.get_host_memory_usage(h)
                telemetry_batch["hosts"].append({
                    "name": h.name, "cpu": cpu, "mem": mem
                })

            # B. Switch Metrics
            for s in net.switches:
                telemetry_batch["switches"].append(s.name)

            # C. Link Metrics
            link_stats = link_collector.collect_link_metrics(net, link_counters, SYNC_INTERVAL)
            for lid, val in link_stats.items():
                telemetry_batch["links"].append({"id": lid, "bw": val})

            # LOG: In ra màn hình để bạn thấy nó đang chạy
            total_bw = sum(d['bw'] for d in telemetry_batch['links'])
            logger.info(f"📡 Gửi dữ liệu: {len(net.hosts)} Hosts | Tổng lưu lượng mạng: {total_bw:.2f} Mbps")
            
            if total_bw > 0:
                # In chi tiết link nào đang có traffic
                active_links = [f"{l['id']}:{l['bw']}M" for l in telemetry_batch['links'] if l['bw'] > 0]
                logger.info(f"    Active Links: {', '.join(active_links)}")

            # Gửi WebSocket
            sio.emit('mininet_telemetry', telemetry_batch)

            # Ngủ bù trừ thời gian xử lý (giúp mượt hơn)
            elapsed = time.time() - start_time
            sleep_time = max(0.1, SYNC_INTERVAL - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        logger.info("\n Đang dừng chương trình...")
    finally:
        if sio.connected:
            sio.disconnect()
        net.stop()
        logger.info(" Đã dọn dẹp Mininet.")

if __name__ == '__main__':
    run_simulation()