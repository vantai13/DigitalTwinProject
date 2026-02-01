import os
import re
import time 
from venv import logger

# ========================================
# ✅ GLOBAL: DICT LƯU TRẠNG THÁI LINK
# ========================================
_link_status_cache = {}  # {link_id: 'up'/'down'}

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
    Thu thập dữ liệu các link với Fast Cut-off khi DOWN
    
    ✅ CHIẾN THUẬT:
    - Nếu link DOWN (status cache) → throughput = 0 ngay lập tức
    - Nếu link UP nhưng throughput = 0 → Áp dụng EMA
    - Reset counter khi link DOWN để tránh spike khi UP lại
    """
    global _link_status_cache

    link_metrics = {}
    ALPHA = 0.7  # Hệ số EMA
    
    for link in net.links:
        node1 = link.intf1.node
        node2 = link.intf2.node
        
        # ID duy nhất
        link_id = "-".join(sorted([node1.name, node2.name]))
        
        # ========================================
        # ✅ BƯỚC 1: KIỂM TRA STATUS CACHE TRƯỚC
        # ========================================
        cached_status = _link_status_cache.get(link_id)
        
        if cached_status == 'down':
            # ✅ FAST CUT-OFF: Link bị tắt → Force = 0 ngay
            link_metrics[link_id] = 0.0
            prev_throughput_tracker[link_id] = 0.0
            
            # ✅ XÓA COUNTER để tránh SPIKE khi UP
            if link_id in link_byte_counters:
                del link_byte_counters[link_id]
            
            logger.debug(f"[LINK_STATS] {link_id} FAST CUT-OFF (status=down)")
            continue
        
        # ========================================
        # ✅ BƯỚC 2: THU THẬP BYTES
        # ========================================
        target_node = None
        target_intf = None
        if 'h' in node1.name: 
            target_node = node1; target_intf = link.intf1.name
        elif 'h' in node2.name:
            target_node = node2; target_intf = link.intf2.name
        else:
            target_node = node1; target_intf = link.intf1.name

        if not target_node: continue

        rx, tx = get_switch_interface_bytes(target_node, target_intf)
        
        # ========================================
        # ✅ BƯỚC 3: TÍNH THROUGHPUT RAW
        # ========================================
        current_throughput = 0.0
        
        if link_id in link_byte_counters:
            (prev_rx, prev_tx) = link_byte_counters[link_id]
            delta_rx = max(0, rx - prev_rx)
            delta_tx = max(0, tx - prev_tx)
            delta_bytes = delta_rx + delta_tx
            
            if sync_interval > 0.001:
                current_throughput = (delta_bytes * 8) / (sync_interval * 1_000_000)
        
        # Cập nhật counter bytes
        link_byte_counters[link_id] = (rx, tx)

        # ========================================
        # ✅ BƯỚC 4: ÁP DỤNG EMA (CHỈ KHI LINK UP)
        # ========================================
        if current_throughput == 0:
            # Throughput = 0 THẬT (không phải do DOWN)
            # → Vẫn áp dụng EMA để giảm dần
            smoothed_throughput = 0.0
        else:
            # Có traffic → EMA bình thường
            if link_id in prev_throughput_tracker:
                old_val = prev_throughput_tracker[link_id]
                smoothed_throughput = (current_throughput * ALPHA) + (old_val * (1 - ALPHA))
            else:
                smoothed_throughput = current_throughput
        
        prev_throughput_tracker[link_id] = smoothed_throughput
        link_metrics[link_id] = round(smoothed_throughput, 2)

    return link_metrics

# ========================================
# ✅ HÀM MỚI: RESET COUNTER KHI LINK UP
# ========================================
def reset_link_counter(link_id):
    """
    Xóa counter của link để tránh tăng vọt khi link bật lại
    
    Args:
        link_id (str): ID của link (h1-s1)
    """
    global link_byte_counters, prev_throughput_tracker
    
    if link_id in link_byte_counters:
        del link_byte_counters[link_id]
        logger.info(f"[LINK_STATS] Reset byte counter for {link_id}")
    
    if link_id in prev_throughput_tracker:
        del prev_throughput_tracker[link_id]
        logger.info(f"[LINK_STATS] Reset throughput tracker for {link_id}")


# ========================================
# ✅ HÀM MỚI: CẬP NHẬT TRẠNG THÁI LINK
# ========================================
def update_link_status(link_id, status):
    """
    Cập nhật trạng thái link từ CommandExecutor
    
    Args:
        link_id (str): ID của link
        status (str): 'up' hoặc 'down'
    """
    global _link_status_cache
    _link_status_cache[link_id] = status
    logger.info(f"[LINK_STATS] Link {link_id} status updated: {status}")

def get_switch_interface_bytes(node, interface_name):
    """
    Đọc RX/TX bytes từ /proc/net/dev với error handling
    
    ✅ FIX:
    - Kiểm tra output có hợp lệ không
    - Retry nếu timeout
    - Fallback về 0,0 nếu lỗi
    """
    max_retries = 2
    timeout = 0.3  # Tăng từ 0.2s lên 0.3s
    
    for attempt in range(max_retries):
        cmd = f'timeout {timeout}s cat /proc/net/dev | grep "{interface_name}:"'
        
        try:
            # Execute command với lock
            cmd_result = ""
            if hasattr(node, 'lock'):
                with node.lock:
                    cmd_result = node.cmd(cmd)
            else:
                cmd_result = node.cmd(cmd)
            
            # ========================================
            # ✅ FIX 1: KIỂM TRA OUTPUT HỢP LỆ
            # ========================================
            if not cmd_result or not cmd_result.strip():
                if attempt < max_retries - 1:
                    continue  # Retry
                return 0, 0
            
            # ========================================
            # ✅ FIX 2: KIỂM TRA TIMEOUT/ERROR MESSAGES
            # ========================================
            error_keywords = ['Connection', 'Terminated', 'closed', 'timeout']
            if any(keyword in cmd_result for keyword in error_keywords):
                if attempt < max_retries - 1:
                    time.sleep(0.1)  # Đợi 100ms trước khi retry
                    continue
                return 0, 0
            
            # ========================================
            # ✅ FIX 3: PARSE VỚI ERROR HANDLING
            # ========================================
            line = cmd_result.strip()
            
            # Kiểm tra format đúng (phải có dấu ':')
            if ':' not in line:
                if attempt < max_retries - 1:
                    continue
                return 0, 0
            
            stats = line.split(':', 1)[1].strip()
            parts = re.split(r'\s+', stats)
            
            # Kiểm tra đủ số field (phải có ít nhất 9 fields)
            if len(parts) < 9:
                if attempt < max_retries - 1:
                    continue
                return 0, 0
            
            # Parse với try-except
            try:
                rx_bytes = int(parts[0])
                tx_bytes = int(parts[8])
                return rx_bytes, tx_bytes
            except (ValueError, IndexError):
                if attempt < max_retries - 1:
                    continue
                return 0, 0
        
        except Exception as e:
            logger.debug(f"[LINK_STATS] Error reading {interface_name} (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(0.1)
                continue
            return 0, 0
    
    # Nếu hết retries
    return 0, 0