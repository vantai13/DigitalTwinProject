import threading
import time
import random
import re
from utils.logger import setup_logger

logger = setup_logger()

# 1. Biến toàn cục để lưu kết quả đo mới nhất (Shared Memory)
# Key: "h1-h2", Value: {latency, loss, jitter}
_metrics_cache = {}
_cache_lock = threading.Lock()
_running = False

def parse_ping_output(output):
    """
    Phân tích kết quả ping để lấy Latency, Loss và Jitter (mdev).
    Output mẫu Linux: "rtt min/avg/max/mdev = 0.045/0.058/0.083/0.012 ms"
    """
    latency = 0.0
    loss = 100.0
    jitter = 0.0

    try:
        # Lấy Packet Loss
        loss_match = re.search(r'(\d+)% packet loss', output)
        if loss_match:
            loss = float(loss_match.group(1))

        # Lấy Latency (avg) và Jitter (mdev)
        # mdev (Mean Deviation) chính là chỉ số Jitter chuẩn nhất của Ping
        rtt_match = re.search(r'rtt min/avg/max/mdev = [\d\.]+/([\d\.]+)/[\d\.]+/([\d\.]+)', output)
        if rtt_match:
            latency = float(rtt_match.group(1))
            jitter = float(rtt_match.group(2))
            
    except Exception as e:
        logger.error(f"Lỗi parse ping: {e}")

    return latency, loss, jitter

def _measurement_loop(net):
    """Vòng lặp chạy ngầm để đo đạc"""
    global _running
    logger.info(">>> Đã khởi động luồng đo Latency/Jitter ngầm...")
    
    while _running:
        try:
            hosts = net.hosts
            if len(hosts) < 2:
                time.sleep(1)
                continue

            # CHỈNH SỬA: Chỉ đo ngẫu nhiên 2 cặp mỗi lần lặp để giảm tải CPU
            # Dần dần sẽ phủ hết mạng, không cần đo tất cả cùng lúc
            pairs_to_measure = []
            for _ in range(2): 
                pairs_to_measure.append(random.sample(hosts, 2))

            for h_src, h_dst in pairs_to_measure:
                pair_id = f"{h_src.name}-{h_dst.name}"

                # KỸ THUẬT TỐI ƯU:
                # Ping 5 gói (-c 5), giãn cách cực nhanh 0.05s (-i 0.05)
                # Tổng thời gian đo chỉ mất ~0.25s nhưng có đủ số liệu thống kê
                cmd = f"ping -c 5 -i 0.05 -W 1 {h_dst.IP()}"
                
                output = h_src.cmd(cmd)
                lat, loss, jit = parse_ping_output(output)

                # Cập nhật vào kho chứa chung
                with _cache_lock:
                    _metrics_cache[pair_id] = {
                        "latency": lat,
                        "loss": loss,
                        "jitter": jit
                    }
                
                # Nghỉ nhẹ giữa các lần ping để CPU thở
                time.sleep(0.1)

            # Nghỉ giữa các vòng đo lớn
            time.sleep(1.0) 

        except Exception as e:
            logger.error(f"Lỗi trong luồng đo metrics: {e}")
            time.sleep(1)

def start_background_measurement(net):
    """Hàm này được gọi 1 lần duy nhất từ main.py"""
    global _running
    if _running: return
    
    _running = True
    t = threading.Thread(target=_measurement_loop, args=(net,), daemon=True)
    t.start()

def measure_path_metrics(net):
    """
    Hàm này được gọi bởi Main Loop mỗi giây.
    Nó trả về dữ liệu NGAY LẬP TỨC từ bộ nhớ đệm, KHÔNG CHỜ PING.
    """
    with _cache_lock:
        # Trả về bản sao để tránh lỗi xung đột dữ liệu
        return _metrics_cache.copy()