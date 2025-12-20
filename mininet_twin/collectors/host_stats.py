# mininet_twin/collectors/host_stats.py

import re
import random
from utils.logger import setup_logger
import os 
import time

logger = setup_logger()

# Dictionary để lưu lần đo trước: { 'h1': {'prev_usage': 12345, 'prev_time': 1600000}, ... }
_cpu_tracker = {}

def get_host_cpu_usage(host):
    """
    Lấy % CPU usage chính xác dựa trên Cgroups (Linux Control Groups).
    Yêu cầu Mininet chạy với host=CPULimitedHost.
    """
    # 1. Xác định đường dẫn file cpuacct của host này
    # Trong Mininet, thường nằm ở /sys/fs/cgroup/cpu,cpuacct/<tên_nhóm>/<tên_host>
    # CPULimitedHost tự động gắn cgroup vào host object
    
    try:
        # Lấy PID của tiếng trình shell trong host ảo
        pid = host.pid 
        
        # Tìm file cpuacct.usage dựa trên cgroup của PID này
        # Đây là cách tổng quát nhất để tìm cgroup path
        cgroup_path = ""
        with open(f"/proc/{pid}/cgroup", "r") as f:
            for line in f:
                if "cpuacct" in line:
                    # line format: 11:cpu,cpuacct:/mininet/h1
                    cgroup_path = line.split(":")[2].strip()
                    break
        
        if not cgroup_path:
            return 0.0

        # Đường dẫn tuyệt đối tới file thống kê
        base_cgroup = "/sys/fs/cgroup/cpu,cpuacct"
        usage_file = f"{base_cgroup}{cgroup_path}/cpuacct.usage"

        # Đọc tổng số nanoseconds CPU đã dùng
        with open(usage_file, "r") as f:
            current_usage_ns = int(f.read().strip())
            
        current_time_ns = time.time_ns() # Thời gian hiện tại (nanoseconds)

        # --- TÍNH TOÁN % ---
        usage_percent = 0.0
        
        if host.name in _cpu_tracker:
            prev = _cpu_tracker[host.name]
            delta_usage = current_usage_ns - prev['usage']
            delta_time = current_time_ns - prev['time']
            
            if delta_time > 0:
                # CPU % = (Thời gian dùng CPU / Tổng thời gian trôi qua) * 100
                # Lưu ý: Nếu máy có nhiều core, con số này có thể > 100% nếu không chia số core
                usage_percent = (delta_usage / delta_time) * 100
        
        # Cập nhật trạng thái để dùng cho vòng lặp sau
        _cpu_tracker[host.name] = {
            'usage': current_usage_ns,
            'time': current_time_ns
        }

        return round(usage_percent, 2)

    except FileNotFoundError:
        # Fallback: Nếu không tìm thấy cgroup (do chưa config CPULimitedHost), dùng cách cũ nhẹ nhàng hơn
        # Dùng ps để lấy %CPU của tiến trình shell (nhẹ hơn top)
        try:
            # Lấy %CPU của chính process host đó
            cmd = f"ps -p {host.pid} -o %cpu --no-headers"
            # Chạy lệnh trên máy thật (không phải host.cmd) để tránh overhead
            output = os.popen(cmd).read().strip()
            if output:
                return float(output)
        except:
            pass
        return 0.0
    except Exception as e:
        logger.error(f"Lỗi đo CPU {host.name}: {e}")
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

        # if hasattr(host, 'lock'):
        #     with host.lock:
        #         cmd_result = host.cmd(cmd)
        # else:
        #     cmd_result = host.cmd(cmd)
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
        # if hasattr(host, 'lock'):
        #     with host.lock:
        #         cmd_result = host.cmd(cmd)
        # else:
        #     cmd_result = host.cmd(cmd)
        cmd_result = host.cmd(cmd)
        logger.info(f"\n[DEBUG] Interfaces của {host.name}:\n{cmd_result}")

    except Exception as e:
        logger.error(f"[Lỗi] list_all_interfaces {host.name}: {e}")