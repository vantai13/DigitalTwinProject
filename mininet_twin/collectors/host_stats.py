# mininet_twin/collectors/host_stats.py

import re
import random
from utils.logger import setup_logger

logger = setup_logger()


def get_host_cpu_usage(host):
    """
    Lấy % CPU sử dụng cho Mininet host (giả lập an toàn).
    """
    try:
        # Dùng timeout để tránh treo vĩnh viễn nếu ps aux bị kẹt
        cmd = "timeout 0.2s ps aux | wc -l"
        output = ""

        if hasattr(host, 'lock'):
            with host.lock:
                output = host.cmd(cmd).strip()
        else:
            output = host.cmd(cmd).strip()

        # Nếu timeout hoặc lỗi → output sẽ rỗng hoặc chứa "Terminated"
        if not output or "Terminated" in output:
            num_processes = 0
        else:
            num_processes = int(output) if output.isdigit() else 0

    except Exception as e:
        logger.debug(f"[CPU] Timeout hoặc lỗi trên {host.name}: {e}")
        num_processes = 0

    # Logic giả lập cũ của bạn (giữ nguyên để tránh đột ngột giảm CPU về 0)
    base_cpu = min(100, num_processes * 0.5)
    cpu_usage = base_cpu + random.uniform(-10, 20)
    cpu_usage = max(0, min(100, cpu_usage))

    return round(cpu_usage, 2)


def get_host_memory_usage(host):
    """Lấy % Memory sử dụng (an toàn với timeout)."""
    cmd_result = ""

    try:
        # Timeout cực ngắn: nếu free -m treo → bỏ qua ngay
        cmd = "timeout 0.2s free -m"

        if hasattr(host, 'lock'):
            with host.lock:
                cmd_result = host.cmd(cmd)
        else:
            cmd_result = host.cmd(cmd)

        # Nếu timeout → cmd_result sẽ rỗng hoặc có từ "Terminated"
        if not cmd_result or "Terminated" in cmd_result:
            raise ValueError("free command timeout")

        for line in cmd_result.splitlines():
            if "Mem:" in line:
                numbers = re.findall(r'\d+', line)
                if len(numbers) >= 3:
                    mem_total = float(numbers[1])   # cột thứ 2 là total
                    mem_used  = float(numbers[2])   # cột thứ 3 là used (chính xác hơn cũ)

                    if mem_total == 0:
                        return 30.0

                    real_percent = (mem_used / mem_total) * 100

                    # Vẫn giữ một chút simulate như cũ để đồ thị không bị nhảy quá đột ngột
                    host_id_str = re.findall(r'\d+', host.name)
                    host_id = int(host_id_str[0]) if host_id_str else 1
                    offset = (host_id * 5) % 20
                    simulated = 30 + offset + random.uniform(-8, 12)

                    # Kết hợp 70% thực + 30% simulate → mượt mà + chính xác
                    final = 0.7 * real_percent + 0.3 * simulated
                    return round(max(10, min(95, final)), 2)

        # Không tìm thấy dòng Mem:
        raise ValueError("No Mem line found")

    except Exception as e:
        logger.debug(f"[Memory] Timeout hoặc lỗi trên {host.name}: {e}")
        # Fallback: dùng simulate hoàn toàn như cũ
        host_id_str = re.findall(r'\d+', host.name)
        host_id = int(host_id_str[0]) if host_id_str else 1
        offset = (host_id * 5) % 20
        simulated_mem = 30 + offset + random.uniform(-5, 10)
        return round(max(10, min(90, simulated_mem)), 2)


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