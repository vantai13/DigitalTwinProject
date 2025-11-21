import threading
import time
import random
import re
import itertools
from utils.logger import setup_logger

logger = setup_logger()


_metrics_cache = {}
_cache_lock = threading.Lock()
_stop_event = threading.Event() #  Dùng Event để quản lý dừng thread an toàn
_thread = None

def parse_ping_output(output):
    """
    Phân tích kết quả ping để lấy Latency, Loss và Jitter (mdev).
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
    logger.info(">>> Luồng đo Latency bắt đầu (Round-Robin Mode)...")
    
    # Tạo danh sách tất cả các cặp có thể có (Pair Generator)
    hosts = net.hosts
    all_pairs = list(itertools.combinations(hosts, 2))
    

    pair_index = 0
    total_pairs = len(all_pairs)
    
    while not _stop_event.is_set():  # vong lap vo tan, den khi co lenh dung
        try:
            if total_pairs == 0:
                time.sleep(1)
                continue


            current_batch = []
            for _ in range(2):
                current_batch.append(all_pairs[pair_index])
                pair_index = (pair_index + 1) % total_pairs 
            
            for h_src, h_dst in current_batch:
                if _stop_event.is_set(): break 

                pair_id = f"{h_src.name}-{h_dst.name}"
                
                
                cmd = f"ping -c 1 -W 0.2 {h_dst.IP()}" 
                output = h_src.cmd(cmd)
                lat, loss, jit = parse_ping_output(output)

                with _cache_lock:
                    _metrics_cache[pair_id] = {
                        "latency": lat,
                        "loss": loss,
                        "jitter": jit
                    }
                
                time.sleep(0.1)

            time.sleep(1.0) 

        except Exception as e:
            logger.error(f"Lỗi luồng đo metrics: {e}")
            time.sleep(1)
    
    logger.info(">>> Luồng đo Latency đã DỪNG.")

def start_background_measurement(net):
    
    global _thread
    _stop_event.clear()
    _thread = threading.Thread(target=_measurement_loop, args=(net,), daemon=True)
    _thread.start()

def stop_background_measurement():
    logger.info("Đang yêu cầu dừng luồng đo...")
    _stop_event.set()
    if _thread:
        _thread.join(timeout=2.0) # Chờ thread kết thúc tối đa 2s

def measure_path_metrics(net):
    """
    Nó trả về dữ liệu NGAY LẬP TỨC từ bộ nhớ đệm, KHÔNG CHỜ PING.
    """
    with _cache_lock:
        # Trả về bản sao để tránh lỗi xung đột dữ liệu
        return _metrics_cache.copy()