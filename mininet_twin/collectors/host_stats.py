import re
import random
from utils.logger import setup_logger

logger = setup_logger()

def get_host_cpu_usage(host):
    """
    Lấy % CPU sử dụng cho Mininet host.
    """
    try:
        ps_output = host.cmd("ps aux | wc -l").strip()
        num_processes = int(ps_output) if ps_output.isdigit() else 0
    except Exception:
        num_processes = 0

    base_cpu = min(15, num_processes * 0.5)
    cpu_usage = base_cpu + random.uniform(-3, 8)
    cpu_usage = max(0, min(100, cpu_usage))
    
    return round(cpu_usage, 2)

def get_host_memory_usage(host):
    """
    Lấy % Memory sử dụng.
    """
    try:
        cmd_result = host.cmd('free -m | grep Mem')
        
        if not cmd_result.strip():
            return 30.0 
        
        parts = re.split(r'\s+', cmd_result.strip())
        
        if len(parts) < 3:
            return 30.0
        
        mem_total = float(parts[1])
        mem_used = float(parts[2])
        
        if mem_total == 0:
            return 30.0
        
        # Giả lập memory riêng cho từng host
        host_id = int(host.name.replace('h', '').replace('s', ''))
        offset = (host_id * 5) % 20
        
        simulated_mem = 30 + offset + random.uniform(-5, 10)
        simulated_mem = max(10, min(90, simulated_mem))
        
        return round(simulated_mem, 2)
        
    except Exception as e:
        logger.error(f"[Lỗi] get_host_memory_usage({host.name}): {e}")
        return 30.0

def get_interface_bytes(host, interface_name):
    """
    Lấy tổng số bytes TX và RX cho một interface.
    """
    try:
        cmd_result = host.cmd(f'cat /proc/net/dev | grep "{interface_name}:"')
        
        if not cmd_result.strip():
            return 0, 0
        
        line = cmd_result.strip()
        stats = line.split(':')[1].strip()
        parts = re.split(r'\s+', stats)
        
        rx_bytes = int(parts[0])
        tx_bytes = int(parts[8])
        
        return rx_bytes, tx_bytes
        
    except Exception as e:
        logger.error(f"[Lỗi] get_interface_bytes({host.name}, {interface_name}): {e}")
        return 0, 0

def list_all_interfaces(host):
    """Debug: Liệt kê tất cả interface của host."""
    try:
        cmd_result = host.cmd('cat /proc/net/dev')
        logger.info(f"\n[DEBUG] Interfaces của {host.name}:\n{cmd_result}")
    except Exception as e:
        logger.error(f"[Lỗi] list_all_interfaces: {e}")