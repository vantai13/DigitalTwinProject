import re
from utils.logger import setup_logger

logger = setup_logger()

# Đổi tên hàm cho đúng bản chất (không chỉ đo latency nữa)
def measure_path_metrics(net):
    """
    Đo Latency và Packet Loss giữa các cặp Host.
    Trả về: Dictionary { 'pair_id': {'latency': ms, 'loss': %}}
    """
    path_metrics = {}
    
    # Lấy danh sách host và chọn cặp ngẫu nhiên (như logic cũ)
    import random
    hosts = net.hosts
    if len(hosts) < 2: return {}

    targets = []
    if len(hosts) <= 5:
        import itertools
        targets = list(itertools.combinations(hosts, 2))
    else:
        for _ in range(3):
             targets.append(random.sample(hosts, 2))

    for h_src, h_dst in targets:
        pair_id = f"{h_src.name}-{h_dst.name}"
        
        try:
            # Ping 1 gói (-c 1), timeout cực ngắn 0.1s (-W 0.1) để test nhanh
            # Lưu ý: -W 0.1 có thể hơi gắt, nếu mạng lag thật có thể tăng lên 0.5
            cmd = f"ping -c 1 -W 0.1 {h_dst.IP()}"
            output = h_src.cmd(cmd)
            
            # 1. Bắt độ trễ (Latency)
            lat_val = -1
            lat_match = re.search(r'time=([\d\.]+)', output)
            if lat_match:
                lat_val = float(lat_match.group(1))
            
            # 2. Bắt gói tin mất (Packet Loss) - Quan trọng
            # Output mẫu: "0% packet loss" hoặc "100% packet loss"
            loss_val = 100 # Mặc định coi như mất hết nếu lỗi
            loss_match = re.search(r'(\d+)% packet loss', output)
            if loss_match:
                loss_val = float(loss_match.group(1))

            # Nếu ping thành công mà loss=0, latency phải > 0
            if lat_val != -1:
                loss_val = 0.0

            path_metrics[pair_id] = {
                "latency": lat_val,
                "loss": loss_val
            }
                
        except Exception as e:
            logger.error(f"Lỗi đo metrics {pair_id}: {e}")
            path_metrics[pair_id] = {"latency": -1, "loss": 100}

    return path_metrics