import re

def collect_link_metrics(net, link_byte_counters, sync_interval):
    """Quét TẤT CẢ các Link và tính toán băng thông."""
    link_metrics = {}
    
    for link in net.links:
        node1 = link.intf1.node
        node2 = link.intf2.node
        
        # Tạo ID duy nhất: sắp xếp tên node để a-b giống b-a
        link_id = "-".join(sorted([node1.name, node2.name]))
        
        target_node = None
        target_intf = None
        
        # Ưu tiên đo trên Host (tên chứa 'h') để chính xác hơn
        if 'h' in node1.name: 
            target_node = node1
            target_intf = link.intf1.name
        elif 'h' in node2.name:
            target_node = node2
            target_intf = link.intf2.name
        else:
            # Link giữa switch-switch
            target_node = node1
            target_intf = link.intf1.name

        if not target_node: continue

        rx, tx = get_switch_interface_bytes(target_node, target_intf)
        
        # Lấy số liệu cũ từ bộ nhớ đệm
        (prev_rx, prev_tx) = link_byte_counters.get(link_id, (0, 0))
        
        delta_bytes = (rx - prev_rx) + (tx - prev_tx)
        delta_bytes = max(0, delta_bytes) # Tránh số âm khi counter bị reset
        
        # Logic cập nhật counter:
        # Chỉ cập nhật nếu đã có dữ liệu cũ (prev_rx > 0) HOẶC dict đã khởi tạo
        if prev_rx > 0 or loop_count_check(link_byte_counters): 
             link_byte_counters[link_id] = (rx, tx)
        else:
             # Lần đầu chạy: chỉ lưu mốc, chưa tính băng thông
             link_byte_counters[link_id] = (rx, tx)
             delta_bytes = 0

        # Công thức: (Bytes * 8 bit) / (Seconds * 1 triệu) = Mbps
        throughput_mbps = round((delta_bytes * 8) / (sync_interval * 1_000_000), 2)
        link_metrics[link_id] = throughput_mbps

    return link_metrics

def get_switch_interface_bytes(node, interface_name):
    """Đọc /proc/net/dev để lấy RX/TX bytes."""
    try:
        cmd_result = node.cmd(f'cat /proc/net/dev | grep "{interface_name}:"')
        
        if not cmd_result.strip():
            return 0, 0
            
        line = cmd_result.strip()
        stats = line.split(':')[1].strip()
        parts = re.split(r'\s+', stats)
        
        # Cột 0: RX bytes, Cột 8: TX bytes
        return int(parts[0]), int(parts[8])
    except Exception:
        return 0, 0
    
def loop_count_check(counters):
    return len(counters) > 0