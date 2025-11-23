import re

# def collect_link_metrics(net, link_byte_counters, sync_interval):
#     """
#     Thu thập dữ liệu các link
#     """
#     link_metrics = {}
#     ALPHA = 0.7  # Hệ số tin tưởng vào giá trị mới (70% mới, 30% cũ)
    
#     for link in net.links:
#         node1 = link.intf1.node
#         node2 = link.intf2.node
        
#         # Tạo ID duy nhất
#         link_id = "-".join(sorted([node1.name, node2.name]))
        
#         target_node = None
#         target_intf = None
        
#         # Ưu tiên đo trên Host
#         if 'h' in node1.name: 
#             target_node = node1
#             target_intf = link.intf1.name
#         elif 'h' in node2.name:
#             target_node = node2
#             target_intf = link.intf2.name
#         else:
#             target_node = node1
#             target_intf = link.intf1.name

#         if not target_node: continue

#         rx, tx = get_switch_interface_bytes(target_node, target_intf)
#         # Tính toán Raw Throughput
#         current_throughput = 0.0
        
#         # Chỉ tính toán nếu link_id ĐÃ CÓ trong bộ đếm từ lần trước
#         if link_id in link_byte_counters:
#             (prev_rx, prev_tx) = link_byte_counters[link_id]
            
#             delta_rx = rx - prev_rx
#             delta_tx = tx - prev_tx
            
#             # Xử lý trường hợp restart hoặc tràn số (counter reset)
#             if delta_rx < 0: delta_rx = 0
#             if delta_tx < 0: delta_tx = 0
            
#             delta_bytes = delta_rx + delta_tx
#         else:
#             # Lần đầu tiên thấy link này -> Chưa tính băng thông
#             delta_bytes = 0
        
#         # Cập nhật số liệu mới nhất
#         link_byte_counters[link_id] = (rx, tx)

#         if sync_interval > 0:
#             throughput_mbps = round((delta_bytes * 8) / (sync_interval * 1_000_000), 2)
#         else:
#             throughput_mbps = 0.0
            
#         link_metrics[link_id] = throughput_mbps

#     return link_metrics

def collect_link_metrics(net, link_byte_counters, prev_throughput_tracker, sync_interval):
    """
    Thu thập dữ liệu các link với kỹ thuật Moving Average (EMA).
    """
    link_metrics = {}
    ALPHA = 0.7  # Hệ số tin tưởng vào giá trị mới (70% mới, 30% cũ)
    
    for link in net.links:
        node1 = link.intf1.node
        node2 = link.intf2.node
        
        # ID duy nhất
        link_id = "-".join(sorted([node1.name, node2.name]))
        
        # ... (Phần xác định target_node giữ nguyên như code cũ) ...
        target_node = None
        target_intf = None
        if 'h' in node1.name: 
            target_node = node1; target_intf = link.intf1.name
        elif 'h' in node2.name:
            target_node = node2; target_intf = link.intf2.name
        else:
            target_node = node1; target_intf = link.intf1.name

        if not target_node: continue

        # Lấy bytes hiện tại (có timeout như đã bàn ở phần trước)
        # rx, tx = get_switch_interface_bytes... (Code cũ)
        # Giả sử bạn đã áp dụng timeout ở bước trước, nếu chưa thì dùng code cũ
        rx, tx = get_switch_interface_bytes(target_node, target_intf)
        
        # Tính toán Raw Throughput
        current_throughput = 0.0
        
        if link_id in link_byte_counters:
            (prev_rx, prev_tx) = link_byte_counters[link_id]
            delta_rx = max(0, rx - prev_rx)
            delta_tx = max(0, tx - prev_tx)
            delta_bytes = delta_rx + delta_tx
            
            if sync_interval > 0.001: # Tránh chia cho 0
                current_throughput = (delta_bytes * 8) / (sync_interval * 1_000_000)
        
        # Cập nhật counter bytes
        link_byte_counters[link_id] = (rx, tx)

        # --- [LOGIC MỚI] ÁP DỤNG MOVING AVERAGE ---
        if link_id in prev_throughput_tracker:
            old_throughput = prev_throughput_tracker[link_id]
            # Công thức EMA
            smoothed_throughput = (current_throughput * ALPHA) + (old_throughput * (1 - ALPHA))
        else:
            # Lần đầu tiên thì không có số cũ
            smoothed_throughput = current_throughput
            
        # Lưu lại để dùng cho vòng lặp sau
        prev_throughput_tracker[link_id] = smoothed_throughput
        
        # Làm tròn 2 số thập phân
        link_metrics[link_id] = round(smoothed_throughput, 2)

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