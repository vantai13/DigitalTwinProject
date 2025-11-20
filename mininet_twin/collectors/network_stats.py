import re
import random
from utils.logger import setup_logger

logger = setup_logger()

def measure_path_metrics(net):
    """
    Đo Latency, Packet Loss (bằng Ping) và Jitter (bằng Iperf UDP).
    Trả về: { 'h1-h2': {'latency': 10.5, 'loss': 0, 'jitter': 0.042} }
    """
    path_metrics = {}
    
    # 1. Lấy danh sách cặp host ngẫu nhiên để đo
    hosts = net.hosts
    if len(hosts) < 2: return {}

    targets = []
    # Chọn ngẫu nhiên tối đa 3 cặp để tránh làm chậm hệ thống
    for _ in range(3):
         targets.append(random.sample(hosts, 2))

    for h_src, h_dst in targets:
        pair_id = f"{h_src.name}-{h_dst.name}"
        metrics = {"latency": -1, "loss": 100, "jitter": -1}
        
        # --- PHẦN 1: ĐO LATENCY & LOSS (Dùng PING) ---
        try:
            # Ping nhanh: 1 gói, timeout 0.5s
            cmd_ping = f"ping -c 1 -W 0.5 {h_dst.IP()}"
            output_ping = ""
            # [SỬA] Thêm Lock
            if hasattr(h_src, 'lock'):
                with h_src.lock:
                    output_ping = h_src.cmd(cmd_ping)
            else:
                output_ping = h_src.cmd(cmd_ping)
            
            # Parse Latency
            lat_match = re.search(r'time=([\d\.]+)', output_ping)
            if lat_match:
                metrics["latency"] = float(lat_match.group(1))
            
            # Parse Loss
            loss_match = re.search(r'(\d+)% packet loss', output_ping)
            if loss_match:
                metrics["loss"] = float(loss_match.group(1))
                
        except Exception as e:
            logger.error(f"[Ping Error] {pair_id}: {e}")

        # --- PHẦN 2: ĐO JITTER (Dùng IPERF UDP) ---
        # Chỉ đo Jitter nếu kết nối Ping thông (Loss < 100)
        if metrics["loss"] < 100:
            try:
                # Iperf Client: Gửi UDP (-u), băng thông nhỏ 1M (-b 1M), thời gian cực ngắn 0.5s (-t 0.5)
                # format output csv (-y C) để dễ parse: timestamp,src_ip,port,dst_ip,port,id,interval,transferred,bandwidth,jitter,errors...
                # Tuy nhiên format chuẩn (mặc định) thường dễ debug hơn với người mới. Ta dùng format mặc định.
                
                cmd_iperf = f"iperf -c {h_dst.IP()} -u -t 0.5 -b 1M"
                output_iperf = ""
                # [SỬA] Thêm Lock
                if hasattr(h_src, 'lock'):
                    with h_src.lock:
                        output_iperf = h_src.cmd(cmd_iperf)
                else:
                    output_iperf = h_src.cmd(cmd_iperf)
                
                # Output mẫu của Iperf UDP Client khi kết thúc:
                # [  3]  0.0- 0.5 sec  64.0 KBytes  1.05 Mbits/sec   0.042 ms    0/   45 (0%)
                # Chúng ta cần tìm con số đứng trước "ms"
                
                # Regex tìm: số chấm động + khoảng trắng + ms
                jitter_match = re.search(r'([\d\.]+)\s+ms', output_iperf)
                if jitter_match:
                    metrics["jitter"] = float(jitter_match.group(1))
                else:
                    metrics["jitter"] = 0.0 # Không bắt được thì coi như 0
                    
            except Exception as e:
                logger.error(f"[Iperf Error] {pair_id}: {e}")
        
        path_metrics[pair_id] = metrics

    return path_metrics