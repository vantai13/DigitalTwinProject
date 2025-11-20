# mininet_twin/collectors/network_stats.py
import re
from utils.logger import setup_logger

logger = setup_logger()

def measure_latency(net):
    """
    Đo độ trễ (Latency) giữa các cặp node đang có liên kết (Link).
    Trả về: Dictionary { 'link_id': latency_ms }
    """
    latency_map = {}
    
    # Duyệt qua tất cả các đường dây (Links) trong mạng
    for link in net.links:
        node1 = link.intf1.node
        node2 = link.intf2.node
        
        # Chỉ đo nếu cả 2 đầu đều là Host (để đơn giản giai đoạn đầu)
        # Hoặc đo từ Host tới Switch.
        # Tốt nhất: Đo giữa 2 đầu của link bất kể là gì, miễn là có IP (Host).
        # Tuy nhiên, Switch OVS thường không có IP gán sẵn ở mức control plane đơn giản.
        # -> Chiến lược: Chỉ đo các Link nối giữa 2 Host (nếu có) 
        # HOẶC tìm cặp Host đại diện đi qua Link đó.
        
        # CÁCH ĐƠN GIẢN NHẤT CHO NGƯỜI MỚI:
        # Chỉ đo độ trễ từ Host -> Host (End-to-End Latency)
        # Nhưng ở đây ta cần latency của Link.
        
        # GIẢI PHÁP THỰC TẾ: 
        # Link trong TopologyView là dây nối.
        # Ta sẽ Ping từ node1 sang node2.
        # Điều kiện: Node 1 và Node 2 phải có IP. (Switch thường không có IP trong Mininet mặc định).
        
        src_node = None
        dst_ip = None
        
        # Case 1: Host nối Host (ít gặp trong mô hình star, nhưng có thể có)
        if 'h' in node1.name and 'h' in node2.name:
            src_node = node1
            dst_ip = node2.IP()
            
        # Case 2: Host nối Switch (Link phổ biến nhất)
        # Switch layer 2 không ping được. Ta sẽ bỏ qua việc đo trực tiếp Link này bằng ping.
        # Thay vào đó, ta sẽ đo End-to-End (Host này ping Host kia).
        pass 

    # --- THAY ĐỔI CHIẾN LƯỢC ---
    # Vì đo từng Link vật lý (Host-Switch) bằng Ping là không khả thi (Switch ko có IP).
    # Ta sẽ chọn ngẫu nhiên các cặp Host để Ping và coi đó là độ trễ của mạng.
    # Nhưng để hiển thị lên Link, ta cần mapping.
    
    # ĐỂ ĐƠN GIẢN HIỂU SÂU: Ta sẽ đo Latency End-to-End giữa các Host nối với nhau qua Switch.
    # Ví dụ: h1 nối s1, h2 nối s1. Ta ping h1 -> h2.
    
    # Code dưới đây thực hiện Ping ngẫu nhiên giữa các host để lấy mẫu
    import random
    
    hosts = net.hosts
    if len(hosts) < 2:
        return {}

    # Chọn ngẫu nhiên 3 cặp để đo (tránh quá tải vòng lặp)
    # Hoặc đo tất cả nếu mạng nhỏ (<10 hosts)
    targets = []
    if len(hosts) <= 5:
        import itertools
        targets = list(itertools.combinations(hosts, 2))
    else:
        for _ in range(3):
             targets.append(random.sample(hosts, 2))

    for h_src, h_dst in targets:
        # Tạo Link ID ảo (Logic hiển thị sau này có thể cần điều chỉnh)
        # Ở đây ta tạm trả về độ trễ giữa các cặp Host
        pair_id = f"{h_src.name}-{h_dst.name}"
        
        try:
            # Lệnh ping: -c 1 (1 gói), -W 0.1 (timeout 0.1s - cực nhanh)
            # Quan trọng: Timeout phải nhỏ để không làm treo vòng lặp chính
            cmd = f"ping -c 1 -W 0.1 {h_dst.IP()}"
            output = h_src.cmd(cmd)
            
            # Phân tích kết quả (Regex)
            # Mẫu: time=0.045 ms
            match = re.search(r'time=([\d\.]+)', output)
            
            if match:
                latency = float(match.group(1))
                latency_map[pair_id] = latency
            else:
                # Packet loss hoặc timeout
                latency_map[pair_id] = -1.0 
                
        except Exception as e:
            logger.error(f"Lỗi ping {pair_id}: {e}")

    return latency_map