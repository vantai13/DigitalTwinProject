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

def start_iperf_traffic(net):
    """
    Khởi động traffic iPerf giữa các host.
    Logic:
    - Host cuối cùng làm Server
    - Các host còn lại làm Client bắn UDP traffic
    """
    if len(net.hosts) < 2:
        logger.warning("Không đủ host để chạy iPerf (cần ít nhất 2)")
        return False
    
    # Chọn server và clients
    server = net.hosts[-1]
    clients = net.hosts[:-1]
    server_ip = server.IP()
    
    logger.info(f"iPerf Server: {server.name} ({server_ip})")
    
    # Khởi động Server (UDP mode, chạy background)
    server.cmd('killall iperf 2>/dev/null')  # Kill process cũ nếu có
    server.cmd('iperf -s -u > /tmp/iperf_server.log 2>&1 &')
    logger.info(f"   → Server started on {server.name}")

    #  Đợi Server sẵn sàng (QUAN TRỌNG!)
    logger.info("Đợi 3 giây để Server khởi động...")
    time.sleep(3)
    
    #  Kiểm tra Server có đang chạy không
    check_result = server.cmd('ps aux | grep "iperf -s" | grep -v grep')
    if not check_result.strip():
        logger.error(" iPerf Server không chạy! Kiểm tra lại.")
        return False
    logger.info("iPerf Server đã sẵn sàng")
    
    #  Khởi động Clients
    for client in clients:
        client.cmd('killall iperf 2>/dev/null')
        
        # Tạo traffic với bandwidth khác nhau cho mỗi client
        # h1: 3M, h2: 5M, h3: 7M, ...
        host_num = int(client.name.replace('h', ''))
        bandwidth = 3 + (host_num - 1) * 2  # 3, 5, 7, 9, ...
        
        cmd = f'iperf -c {server_ip} -u -b {bandwidth}M -t 999999 > /tmp/iperf_{client.name}.log 2>&1 &'
        client.cmd(cmd)
        logger.info(f"   → {client.name} → {server.name} | {bandwidth} Mbps")
    
    #  Verify clients đang chạy
    time.sleep(1)
    running_clients = 0
    for client in clients:
        check = client.cmd('ps aux | grep "iperf -c" | grep -v grep')
        if check.strip():
            running_clients += 1
    
    logger.info(f"iPerf started: {running_clients}/{len(clients)} clients running")
    return True

def run_simulation():
    # Khởi tạo Mininet
    logger.info(" Khởi tạo mạng Mininet...")
    topo = ConfigTopo()
    # net = Mininet(topo=topo)
    net = Mininet(topo=topo, switch=OVSKernelSwitch)
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
    if not start_iperf_traffic(net):
        logger.warning(" iPerf không khởi động được, nhưng tiếp tục chạy...")

    # 5. Main Loop - Thu thập và gửi dữ liệu
    logger.info("=" * 70)
    logger.info(" BẮT ĐẦU VÒNG LẶP THU THẬP DỮ LIỆU")
    logger.info("=" * 70)
    
    link_counters = {}
    loop_count = 0

    try:
        while True:
            loop_count += 1
            start_time = time.time()
            
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
                SYNC_INTERVAL
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