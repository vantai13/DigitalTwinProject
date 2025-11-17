import re
from mininet.node import Host
import collector

def collect_link_metrics(net, link_byte_counters, sync_interval):
    """
    Thu thập metrics cho tất cả các Link TRÊN CẠNH (edge links) của mạng.
    
     không đo switch-switch. Chúng ta đo host-switch,
    vì đó là nơi duy nhất có thể đọc /proc/net/dev để thấy traffic.
    
    Trả về một dictionary: { "link_id": throughput_mbps }
    """
    
    link_metrics = {}
    
    # Lặp qua các Host, vì đó là nơi đo được
    for host in net.hosts:
        # host.intfs là một dictionary, ví dụ { 0: h1-eth0 }
        # Lấy interface đầu tiên (không phải 'lo')
        for intf in host.intfs.values():
            if intf.name == 'lo':
                continue
                
            # Tìm Link
            link = intf.link
            if not link:
                continue
                
            # Tìm 2 node của link
            node1 = link.intf1.node
            node2 = link.intf2.node
            link_id = "-".join(sorted([node1.name, node2.name]))

            #  Lấy số bytes (chỉ từ phía Host)
            # Chúng ta không cần đo 2 chiều, vì tx(h1) == rx(s1)
            # và rx(h1) == tx(s1).
            current_rx, current_tx = collector.get_interface_bytes(host, intf.name)
            
            # Lấy giá trị cũ
            (prev_rx, prev_tx) = link_byte_counters.get(link_id, (0, 0))

            # Tính toán
            delta_bytes = (current_rx - prev_rx) + (current_tx - prev_tx)
            delta_bytes = max(0, delta_bytes) # Tránh số âm khi reset
            
            throughput_bps = delta_bytes / sync_interval
            throughput_mbps = round((throughput_bps * 8) / 1_000_000, 2)

            #  Lưu kết quả và bộ nhớ
            link_metrics[link_id] = throughput_mbps
            link_byte_counters[link_id] = (current_rx, current_tx)
            
            break 
            
    return link_metrics