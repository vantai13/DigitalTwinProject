# mininet_twin/collectors/switch_stats.py
import re
import time
from utils.logger import setup_logger

logger = setup_logger()

# Cache để lưu kết quả và thời gian lần đo cuối
_switch_cache = {}
_last_measure_time = 0
MEASURE_INTERVAL = 5.0  

def collect_switch_port_stats(net):
    """
    Thu thập thông số từng cổng của tất cả Switch trong mạng.
    """

    global _last_measure_time, _switch_cache
    current_time = time.time()
    # Nếu chưa đến lúc đo lại, trả về kết quả cũ (Cache)
    if current_time - _last_measure_time < MEASURE_INTERVAL and _switch_cache:
        return _switch_cache

    switch_metrics = {}

    for sw in net.switches:
        sw_name = sw.name
        switch_metrics[sw_name] = {}
        
        try:
            cmd = f"ovs-ofctl dump-ports {sw_name}"
            output = sw.cmd(cmd)
            #logger.info(f"[DEBUG OVS] {sw_name} Output:\n{output}")
            
            # # Xử lý text trả về (Parsing)
            # current_port = None
            
            # for line in output.split('\n'):
            #     line = line.strip()
            #     port_match = re.search(r'port\s+"([^"]+)":', line, re.IGNORECASE)
            #     if port_match:
            #         current_port = port_match.group(1)
            #         switch_metrics[sw_name][current_port] = {
            #             "rx_packets": 0, "tx_packets": 0,
            #             "rx_bytes": 0, "tx_bytes": 0,
            #             "dropped": 0, "errors": 0
            #         }
                
                # Nếu đang ở trong context của một port, bắt dữ liệu RX/TX
            current_port = None
            for line in output.split('\n'):
                line = line.strip()
                port_match = re.search(r'port\s+"([^"]+)":', line, re.IGNORECASE)
                if port_match:
                    current_port = port_match.group(1)
                    switch_metrics[sw_name][current_port] = {
                        "switch_name": sw_name,  
                        "port_name": current_port,
                        "rx_packets": 0, "tx_packets": 0,
                        "rx_bytes": 0, "tx_bytes": 0,
                        "dropped": 0, "errors": 0
                    }
                    
                if current_port:
                    if "rx pkts=" in line:
                        rx_match = re.search(r'rx pkts=(\d+).*bytes=(\d+).*drop=(\d+).*errs=(\d+)', line)
                        if rx_match:
                            stats = switch_metrics[sw_name][current_port]
                            stats["rx_packets"] = int(rx_match.group(1))
                            stats["rx_bytes"] = int(rx_match.group(2))
                            stats["dropped"] += int(rx_match.group(3))
                            stats["errors"] += int(rx_match.group(4))
                    elif "tx pkts=" in line:
                        tx_match = re.search(r'tx pkts=(\d+).*bytes=(\d+).*drop=(\d+).*errs=(\d+)', line)
                        if tx_match:
                            stats = switch_metrics[sw_name][current_port]
                            stats["tx_packets"] = int(tx_match.group(1))
                            stats["tx_bytes"] = int(tx_match.group(2))
                            stats["dropped"] += int(tx_match.group(3))
                            stats["errors"] += int(tx_match.group(4))

        except Exception as e:
            logger.error(f"Lỗi lấy switch stats {sw_name}: {e}")

    _switch_cache = switch_metrics
    _last_measure_time = current_time

    return switch_metrics