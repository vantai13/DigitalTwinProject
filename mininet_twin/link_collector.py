import re
from mininet.node import Host
import collector

def collect_link_metrics(net, link_byte_counters, sync_interval):
    """
     Quét TẤT CẢ các Link (Host-Switch VÀ Switch-Switch)
    """
    link_metrics = {}
    
    # Lặp qua tất cả các đường dây trong mạng
    for link in net.links:
        node1 = link.intf1.node
        node2 = link.intf2.node
        
        # Tạo ID 
        link_id = "-".join(sorted([node1.name, node2.name]))
        
        target_node = None
        target_intf = None
        
        
        if 'h' in node1.name: 
            target_node = node1
            target_intf = link.intf1.name
        elif 'h' in node2.name:
            target_node = node2
            target_intf = link.intf2.name
        else:
            target_node = node1
            target_intf = link.intf1.name

        if not target_node: continue

        rx, tx = get_switch_interface_bytes(target_node, target_intf)
        
        # Tính toán Bandwidth (Mbps)
        (prev_rx, prev_tx) = link_byte_counters.get(link_id, (0, 0))
        
        delta_bytes = (rx - prev_rx) + (tx - prev_tx)
        delta_bytes = max(0, delta_bytes) # Tránh âm
        
        # Cập nhật bộ nhớ đếm (chỉ update nếu có dữ liệu mới hợp lệ)
        if prev_rx > 0 or loop_count_check(link_byte_counters): 
             link_byte_counters[link_id] = (rx, tx)
        else:
             # Lần đầu tiên chạy, chưa tính delta, chỉ lưu lại
             link_byte_counters[link_id] = (rx, tx)
             delta_bytes = 0

        throughput_mbps = round((delta_bytes * 8) / (sync_interval * 1_000_000), 2)
        link_metrics[link_id] = throughput_mbps

    return link_metrics

def get_switch_interface_bytes(node, interface_name):
    """
    Đọc thông số từ interface của Switch (thường nằm ở root namespace).
    Sử dụng lệnh cat /proc/net/dev hệ thống.
    """
    try:
        # Switch trong Mininet thường chạy ở root namespace, 
        # ta có thể đọc trực tiếp file hệ thống hoặc dùng node.cmd
        cmd_result = node.cmd(f'cat /proc/net/dev | grep "{interface_name}:"')
        
        if not cmd_result.strip():
            return 0, 0
            
        line = cmd_result.strip()
        stats = line.split(':')[1].strip()
        parts = re.split(r'\s+', stats)
        
        # Cột 0: RX bytes, Cột 8: TX bytes
        return int(parts[0]), int(parts[8])
    except Exception as e:
        # print(f"[Warn] Không đọc được interface {interface_name} trên {node.name}")
        return 0, 0
    
def loop_count_check(counters):
    # check xem dictionary có dữ liệu chưa
    return len(counters) > 0