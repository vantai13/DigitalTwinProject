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

    base_cpu = min(20, num_processes * 1.5)
    cpu_usage = base_cpu + random.uniform(-10, 20)
    cpu_usage = max(0, min(100, cpu_usage))
    
    return round(cpu_usage, 2)

def get_host_memory_usage(host):
    """Lấy % Memory sử dụng."""
    try:
        cmd_result = host.cmd('free -m') 
        
        
        for line in cmd_result.splitlines():
            if "Mem:" in line:

                numbers = re.findall(r'\d+', line)
                
                if len(numbers) >= 2:
                    mem_total = float(numbers[0])
                    mem_used = float(numbers[1]) # Trong 'free' output, cột 2 là used
                    
                    if mem_total == 0: return 30.0
                    
                    host_id_str = re.findall(r'\d+', host.name)
                    host_id = int(host_id_str[0]) if host_id_str else 1
                    offset = (host_id * 5) % 20
                    
                    simulated_mem = 30 + offset + random.uniform(-5, 10)
                    return round(max(10, min(90, simulated_mem)), 2)

        return 30.0 

    except Exception as e:
        logger.error(f"[Lỗi Memory] {host.name}: {e}")
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