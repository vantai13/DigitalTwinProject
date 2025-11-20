# mininet_twin/collectors/switch_stats.py
import re
from utils.logger import setup_logger

logger = setup_logger()

def collect_switch_port_stats(net):
    """
    Thu thập thông số từng cổng của tất cả Switch trong mạng.
    Trả về: Dictionary { 's1': { 's1-eth1': {'rx_packets': 100, 'tx_packets': 200, 'dropped': 0, 'errors': 0} ... } }
    """
    switch_metrics = {}

    for sw in net.switches:
        sw_name = sw.name
        switch_metrics[sw_name] = {}
        
        try:
            # Lệnh lấy thống kê port từ Open vSwitch
            # output mẫu:
            # Port "s1-eth1": rx pkts=100, bytes=1200, drop=0, errs=0, frame=0...
            #                 tx pkts=200, bytes=2400, drop=0, errs=0, coll=0...
            cmd = f"ovs-ofctl dump-ports {sw_name}"
            output = sw.cmd(cmd)
            logger.info(f"[DEBUG OVS] {sw_name} Output:\n{output}")
            
            # Xử lý text trả về (Parsing)
            current_port = None
            
            for line in output.split('\n'):
                line = line.strip()
                
                # Tìm dòng bắt đầu bằng: Port "tên-port":
                port_match = re.search(r'port\s+"([^"]+)":', line, re.IGNORECASE)
                if port_match:
                    current_port = port_match.group(1)
                    # Khởi tạo dict cho port này
                    switch_metrics[sw_name][current_port] = {
                        "rx_packets": 0, "tx_packets": 0,
                        "rx_bytes": 0, "tx_bytes": 0,
                        "dropped": 0, "errors": 0
                    }
                
                # Nếu đang ở trong context của một port, bắt dữ liệu RX/TX
                if current_port:
                    # Bắt dòng RX (Receive)
                    # rx pkts=100, bytes=1200, drop=0, errs=0
                    if "rx pkts=" in line:
                        rx_match = re.search(r'rx pkts=(\d+).*bytes=(\d+).*drop=(\d+).*errs=(\d+)', line)
                        if rx_match:
                            stats = switch_metrics[sw_name][current_port]
                            stats["rx_packets"] = int(rx_match.group(1))
                            stats["rx_bytes"] = int(rx_match.group(2))
                            stats["dropped"] += int(rx_match.group(3)) # RX drop
                            stats["errors"] += int(rx_match.group(4))  # RX err
                            
                    # Bắt dòng TX (Transmit)
                    # tx pkts=200, bytes=2400, drop=0, errs=0
                    elif "tx pkts=" in line:
                        tx_match = re.search(r'tx pkts=(\d+).*bytes=(\d+).*drop=(\d+).*errs=(\d+)', line)
                        if tx_match:
                            stats = switch_metrics[sw_name][current_port]
                            stats["tx_packets"] = int(tx_match.group(1))
                            stats["tx_bytes"] = int(tx_match.group(2))
                            stats["dropped"] += int(tx_match.group(3)) # Cộng dồn TX drop
                            stats["errors"] += int(tx_match.group(4))  # Cộng dồn TX err

        except Exception as e:
            logger.error(f"Lỗi lấy switch stats {sw_name}: {e}")

    return switch_metrics