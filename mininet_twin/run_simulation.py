import time
import requests
import re
import sys
import os
import link_collector
import json
from mininet.net import Mininet
from mininet.topo import Topo
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.node import Host, Switch
import collector
from topo import ConfigTopo
import logging

# ============================================
# CẤU HÌNH LOGGING CHUẨN PRODUCTION CHO MININET
# ============================================
os.makedirs("logs", exist_ok=True)  # Tạo thư mục logs nếu chưa có

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)-8s] %(message)s',
    handlers=[
        logging.FileHandler("logs/mininet.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger()


# Địa chỉ server Flask (Backend)
API_BASE_URL = "http://localhost:5000/api" 

# Thời gian nghỉ giữa các lần đồng bộ (tính bằng giây)
SYNC_INTERVAL = 2.0 

# --- HÀM GỬI DỮ LIỆU (PUSH FUNCTIONS) ---
def push_host_data_to_api(hostname, cpu_usage, mem_usage):
    """Gửi (POST) dữ liệu metrics của Host lên Flask API."""
    url = f"{API_BASE_URL}/update/host/{hostname}"
    payload = {
        "cpu": cpu_usage,
        "memory": mem_usage
    }
    
    try:
        response = requests.post(url, json=payload, timeout=1.0)
        # Nếu server trả về lỗi (ví dụ 404, 500)
        response.raise_for_status() 
        
    except requests.exceptions.ConnectionError:
        # Bỏ qua lỗi kết nối (vì chúng ta đã xử lý ở vòng lặp chính)
        pass
    except requests.exceptions.RequestException as e:
        # Bắt các lỗi khác (timeout, 404, 500...)
        logger.warning(f"Không thể đẩy dữ liệu host {hostname}: {e}")

def push_link_data_to_api(link_id, throughput_mbps):
    """Gửi (POST) dữ liệu metrics của Link lên Flask API."""
    
    # API endpoint chúng ta SẼ TẠO ở Bước 3
    url = f"{API_BASE_URL}/update/link/{link_id}"
    
    payload = {
        "throughput": throughput_mbps,
        "latency": 0.0 # (Bạn có thể thêm logic `ping` để lấy cái này)
    }
    
    try:
        response = requests.post(url, json=payload, timeout=1.0)
        response.raise_for_status() 
    except requests.exceptions.ConnectionError:
        pass
    except requests.exceptions.RequestException as e:
        logger.warning(f"Không thể đẩy dữ liệu link {link_id}: {e}")

def push_switch_heartbeat_to_api(switch_name):
    """Gửi tín hiệu 'còn sống' nhân tạo cho Switch."""
    url = f"{API_BASE_URL}/update/switch/{switch_name}/heartbeat"
    try:
        requests.post(url, timeout=0.5)
    except Exception:
        pass

def push_topology_to_backend(net):
    """
    Gửi toàn bộ topology (hosts, switches, links) từ đối tượng 'net'
    lên Backend để Backend tự động 'mồi' (seed).
    """
    logger.info("Đang thu thập topology từ Mininet để gửi lên Backend...")

    topology_data = {
        "hosts": [],
        "switches": [],
        "links": []
    }

    # Thu thập thông tin tất cả Hosts
    for host in net.hosts:
        topology_data["hosts"].append({
            "name": host.name,
            "ip": host.IP(),  # Lấy IP thật từ Mininet
            "mac": host.MAC()  # Lấy MAC thật từ Mininet
        })

    # Thu thập thông tin tất cả Switches
    for switch in net.switches:
        topology_data["switches"].append({
            "name": switch.name,
            "dpid": switch.dpid
        })

    #  Thu thập thông tin tất cả Links
    processed_links = set()  # Tránh trùng lặp (h1-s1 và s1-h1) và khi tạo lộn một link gióng như vậy sẽ bị bỏ qua và không xử lý

    for link in net.links:
        node1_name = link.intf1.node.name
        node2_name = link.intf2.node.name

        # Chuẩn hóa link_id (sắp xếp theo alphabet)
        link_id = "-".join(sorted([node1_name, node2_name]))

        if link_id in processed_links:
            continue
        processed_links.add(link_id)

        # Lấy băng thông (bandwidth) nếu có
        bw = 100  # Mặc định
        if 'bw' in link.intf1.params:
            bw = link.intf1.params['bw']
        elif 'bw' in link.intf2.params:
            bw = link.intf2.params['bw']

        topology_data["links"].append({
            "node1": node1_name,
            "node2": node2_name,
            "bandwidth": bw
        })

    # Gửi POST request
    try:
        url = f"{API_BASE_URL}/init/topology"
        response = requests.post(url, json=topology_data, timeout=3.0)
        response.raise_for_status() # Báo lỗi nếu API trả về 4xx/5xx
        logger.info(f"Gửi topology thành công! "
                        f"{len(topology_data['hosts'])} hosts, "
                        f"{len(topology_data['switches'])} switches, "
                        f"{len(topology_data['links'])} links")
        return True

    except requests.exceptions.ConnectionError:
        logger.error(f"[LỖI NGHIÊM TRỌNG] Không thể kết nối đến Backend tại {url}.")
        logger.error(">>> Hãy đảm bảo Backend Flask đang chạy!")
        return False
    except Exception as e:
        logger.error(f"[LỖI] Không thể gửi topology: {e}")
        return False

# --- HÀM CHÍNH ĐỂ CHẠY ---
def run_simulation():
    # setLogLevel('info')
    
    # Khởi tạo mạng
    topo = ConfigTopo()
    net = Mininet(topo=topo)
    net.start()

    # Gửi topology vừa xây dựng lên Backend
    if not push_topology_to_backend(net):
        logger.error("Không thể khởi tạo topology → DỪNG mô phỏng")
        net.stop()
        return

    # -------------------------------------------------
    # KHỞI ĐỘNG IPERF ĐỘNG (DYNAMIC)
    # -------------------------------------------------
    if len(net.hosts) < 2:
        logger.warning("[Lỗi] Cần ít nhất 2 host trong topology để khởi động iPerf.")
    else:
        # Chọn host cuối cùng làm Server
        server = net.hosts[-1]
        server_ip = server.IP()
        logger.info(f">>> Khởi động iPerf server trên {server.name} ({server_ip})...")
        server.cmd('iperf -s -u &') # UDP server, chạy nền
        time.sleep(1) # Đợi server khởi động

        # Cho tất cả host khác làm Client
        client_hosts = net.hosts[:-1] # Lấy tất cả trừ host cuối
        
        # Tạo traffic khác nhau cho đa dạng
        traffic_rates = ["5M", "8M", "3M", "6M"] 
        
        for i, client in enumerate(client_hosts):
            rate = traffic_rates[i % len(traffic_rates)] # Chọn tỉ lệ traffic
            logger.info(f">>> Khởi động iPerf client trên {client.name} (gửi {rate} đến {server.name})...")
            client.cmd(f'iperf -c {server_ip} -u -b {rate} -t 999999 &')
    
    logger.info(" Mạng Mininet đã khởi động...")
    logger.info("Bắt đầu vòng lặp đồng bộ hóa Digital Twin...")

    try:
        # "Bộ nhớ" để lưu trữ số bytes của lần lặp trước
        link_byte_counters = {}

        # collector.list_all_interfaces(h1)
        # collector.list_all_interfaces(h2)

        for i in range(len(net.hosts)):
            collector.list_all_interfaces(net.hosts[i])
        # ---------------------------------------------
        # VÒNG LẶP ĐỒNG BỘ HÓA (THE SYNC LOOP)
        # ---------------------------------------------
        while True:
            # ---  XỬ LÝ HOSTS ---
            for host in net.hosts:
                cpu = collector.get_host_cpu_usage(host)
                mem = collector.get_host_memory_usage(host)
                logger.info(f"[{host.name}] CPU: {cpu}% | Mem: {mem}%")
                push_host_data_to_api(host.name, cpu, mem)

            # ---  XỬ LÝ SWITCHES ---
            for switch in net.switches:
                push_switch_heartbeat_to_api(switch.name)

            # ---  XỬ LÝ LINKS  ---
            link_metrics = link_collector.collect_link_metrics(
                net, link_byte_counters, SYNC_INTERVAL
            )
            
            for link_id, throughput in link_metrics.items():
                logger.info(f"[{link_id}] Bidirectional Throughput: {throughput} Mbps")
                push_link_data_to_api(link_id, throughput)

            # ---  NGHỈ ---
            time.sleep(SYNC_INTERVAL)
        
            
    except KeyboardInterrupt:
        logger.info("\n>>> Đã nhận lệnh dừng (Ctrl+C). Đang dọn dẹp...")
    except requests.exceptions.ConnectionError:
        # Lỗi này xảy ra nếu Flask server CHƯA CHẠY
        logger.error("\n[LỖI] Không thể kết nối đến Backend Flask tại " + API_BASE_URL)
        logger.warning(">>> Hãy đảm bảo server Flask đang chạy!")
    finally:
        # Dọn dẹp Mininet
        net.stop()
        logger.info(">>> Mạng Mininet đã dừng.")


if __name__ == '__main__':
    run_simulation()