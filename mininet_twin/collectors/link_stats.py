import re

def collect_link_metrics(net, link_byte_counters, sync_interval):
    """
    Thu thập dữ liệu các link
    """
    link_metrics = {}
    
    for link in net.links:
        node1 = link.intf1.node
        node2 = link.intf2.node
        
        # Tạo ID duy nhất
        link_id = "-".join(sorted([node1.name, node2.name]))
        
        target_node = None
        target_intf = None
        
        # Ưu tiên đo trên Host
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
        
        # Chỉ tính toán nếu link_id ĐÃ CÓ trong bộ đếm từ lần trước
        if link_id in link_byte_counters:
            (prev_rx, prev_tx) = link_byte_counters[link_id]
            
            delta_rx = rx - prev_rx
            delta_tx = tx - prev_tx
            
            # Xử lý trường hợp restart hoặc tràn số (counter reset)
            if delta_rx < 0: delta_rx = 0
            if delta_tx < 0: delta_tx = 0
            
            delta_bytes = delta_rx + delta_tx
        else:
            # Lần đầu tiên thấy link này -> Chưa tính băng thông
            delta_bytes = 0
        
        # Cập nhật số liệu mới nhất
        link_byte_counters[link_id] = (rx, tx)

        if sync_interval > 0:
            throughput_mbps = round((delta_bytes * 8) / (sync_interval * 1_000_000), 2)
        else:
            throughput_mbps = 0.0
            
        link_metrics[link_id] = throughput_mbps

    return link_metrics

def get_switch_interface_bytes(node, interface_name):
    try:
        # TƯ DUY MỚI: Thêm "timeout 0.2s" vào trước lệnh
        # Nếu lệnh cat bị treo, Linux sẽ kill nó sau 0.2s, trả về rỗng
        cmd = f'timeout 0.2s cat /proc/net/dev | grep "{interface_name}:"'

        # [Quan trọng] Sử dụng lock nếu node là Host (để tránh xung đột với Traffic Gen)
        cmd_result = ""
        if hasattr(node, 'lock'): 
             with node.lock:
                 cmd_result = node.cmd(cmd)
        else:
             cmd_result = node.cmd(cmd)

        if not cmd_result.strip(): return 0, 0
        
        line = cmd_result.strip()
        stats = line.split(':')[1].strip()
        parts = re.split(r'\s+', stats)
        return int(parts[0]), int(parts[8])
    except Exception:
        return 0, 0