# mininet_twin/collectors/host_stats.py

import re
import random
from utils.logger import setup_logger

logger = setup_logger()


def get_host_cpu_usage(host):
    """
    Lấy % CPU load thực tế (dựa trên Load Average hoặc ps).
    Lưu ý: Mininet host dùng chung Kernel nên khó tách CPU % chính xác từng host 
    nếu không dùng cgroups. Cách tốt nhất là dùng 'uptime' để lấy Load Avg chung 
    hoặc ps để đếm mức độ bận rộn của tiến trình shell.
    """
    try:
        # Cách 1: Lấy Load Average của hệ thống (phản ánh độ nghẽn chung)
        # cmd = "uptime | awk -F'load average:' '{ print $2 }' | cut -d, -f1"
        
        # Cách 2 (Tốt hơn cho bài tập): Tính CPU dựa trên %CPU của tiến trình processes
        # Lệnh này lấy tổng %CPU của tất cả process thuộc user hiện tại (hoặc trong context)
        # Tuy nhiên đơn giản nhất là lấy Load Average * 10 (giả lập scale) hoặc parse /proc/stat
        
        # Ở đây mình dùng cách lấy Load Average 1 phút, vì nó phản ánh thực tế máy đang gồng gánh thế nào
        output = host.cmd("cat /proc/loadavg").strip()
        # Output ví dụ: 0.15 0.08 0.02 1/742 3425
        parts = output.split()
        if parts:
            load_1min = float(parts[0])
            # Quy đổi Load Avg ra thang 100 (Ví dụ: máy 4 core, load 4.0 = 100%)
            # Giả sử máy ảo của bạn có 2 vCPU
            cpu_usage = (load_1min / 2.0) * 100
            return round(min(100.0, cpu_usage), 2)
            
    except Exception:
        return 0.0
    
    return 0.0

def get_host_memory_usage(host):
    """
    Lấy % Memory THẬT từ lệnh free -m.
    Không dùng random nữa.
    """
    try:
        # Chạy lệnh free -m
        output = host.cmd('free -m')
        
        # Parse output
        #              total        used        free      shared  buff/cache   available
        # Mem:          7936        1542        4521          13        1872        6124
        
        for line in output.splitlines():
            if "Mem:" in line:
                # Dùng regex để tách số, xử lý cả khoảng trắng nhiều
                parts = re.findall(r'\d+', line)
                if len(parts) >= 2:
                    total_mem = float(parts[0])
                    used_mem = float(parts[1])
                    
                    if total_mem == 0: return 0.0
                    
                    # Tính % thực tế
                    real_usage = (used_mem / total_mem) * 100
                    return round(real_usage, 2)

        return 0.0 

    except Exception as e:
        logger.error(f"[Lỗi Memory] {host.name}: {e}")
        return 0.0

def get_interface_bytes(host, interface_name):
    """
    Lấy tổng số bytes TX và RX cho một interface (với timeout bảo vệ).
    """
    try:
        cmd = f'timeout 0.2s cat /proc/net/dev | grep "{interface_name}:"'

        if hasattr(host, 'lock'):
            with host.lock:
                cmd_result = host.cmd(cmd)
        else:
            cmd_result = host.cmd(cmd)

        # Timeout → trả về rỗng hoặc "Terminated"
        if not cmd_result or "Terminated" in cmd_result:
            return 0, 0

        line = cmd_result.strip()
        if not line:
            return 0, 0

        stats = line.split(':', 1)[1].strip()
        parts = re.split(r'\s+', stats)

        rx_bytes = int(parts[0])
        tx_bytes = int(parts[8])

        return rx_bytes, tx_bytes

    except Exception as e:
        logger.debug(f"[Interface bytes] Lỗi {host.name}-{interface_name}: {e}")
        return 0, 0


def list_all_interfaces(host):
    """Debug: Liệt kê tất cả interface của host (cũng thêm timeout)."""
    try:
        cmd = "timeout 0.5s cat /proc/net/dev"  # Cho debug thì timeout dài hơn chút
        if hasattr(host, 'lock'):
            with host.lock:
                cmd_result = host.cmd(cmd)
        else:
            cmd_result = host.cmd(cmd)

        logger.info(f"\n[DEBUG] Interfaces của {host.name}:\n{cmd_result}")

    except Exception as e:
        logger.error(f"[Lỗi] list_all_interfaces {host.name}: {e}")