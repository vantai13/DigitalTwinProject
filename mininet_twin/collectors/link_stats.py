import re
import time
from utils.logger import logger

# Cache interface bytes để tránh đọc quá nhiều
_interface_cache = {}
_cache_ttl = 0.5  # Cache 500ms (ngắn hơn memory vì cần update nhanh)

def collect_link_metrics(net, link_byte_counters, sync_interval):
    """Thu thập throughput cho tất cả các link."""
    link_metrics = {}
    
    for link in net.links:
        node1 = link.intf1.node
        node2 = link.intf2.node
        
        link_id = "-".join(sorted([node1.name, node2.name]))
        
        # Chọn node để đo
        if 'h' in node1.name:
            target_node, target_intf = node1, link.intf1.name
        elif 'h' in node2.name:
            target_node, target_intf = node2, link.intf2.name
        else:
            target_node, target_intf = node1, link.intf1.name
        
        # Đọc bytes với cache
        rx, tx = _get_interface_bytes_cached(target_node, target_intf)
        
        # Tính delta
        if link_id in link_byte_counters:
            prev_rx, prev_tx = link_byte_counters[link_id]
            delta_bytes = max(0, (rx - prev_rx) + (tx - prev_tx))
        else:
            delta_bytes = 0
        
        link_byte_counters[link_id] = (rx, tx)
        
        # Tính throughput
        if sync_interval > 0 and delta_bytes > 0:
            throughput = round((delta_bytes * 8) / (sync_interval * 1_000_000), 2)
        else:
            throughput = 0.0
        
        link_metrics[link_id] = throughput
    
    return link_metrics


def _get_interface_bytes_cached(node, interface_name):
    """Đọc bytes với cache để tránh concurrent poll."""
    global _interface_cache
    
    cache_key = f"{node.name}:{interface_name}"
    current_time = time.time()
    
    # Check cache
    if cache_key in _interface_cache:
        cached_value, timestamp = _interface_cache[cache_key]
        if current_time - timestamp < _cache_ttl:
            return cached_value
    
    # Đọc mới
    rx, tx = _get_interface_bytes(node, interface_name)
    _interface_cache[cache_key] = ((rx, tx), current_time)
    
    return rx, tx


def _get_interface_bytes(node, interface_name):
    """Đọc RX/TX bytes từ /proc/net/dev với retry."""
    for attempt in range(2):  # Thử 2 lần thôi (link cần nhanh)
        try:
            cmd_result = node.cmd(
                f'cat /proc/net/dev 2>/dev/null | grep "{interface_name}:"',
                timeout=0.5
            )
            
            if not cmd_result.strip():
                return 0, 0
            
            line = cmd_result.strip()
            stats = line.split(':')[1].strip()
            parts = re.split(r'\s+', stats)
            
            if len(parts) >= 9:
                return int(parts[0]), int(parts[8])
            else:
                return 0, 0
                
        except Exception as e:
            if 'concurrent poll()' in str(e) and attempt < 1:
                time.sleep(0.05)  # Đợi 50ms
                continue
            else:
                return 0, 0
    
    return 0, 0