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
    logger.info(">>> Luồng đo Latency bắt đầu (Random Sampling Mode)...")
    
    # Tạo danh sách tất cả các cặp có thể có (Pair Generator)
    hosts = net.hosts
    MAX_SAMPLES_PER_CYCLE = 10  # CHỈNH SỬA: Giới hạn số cặp đo mỗi vòng lặp
    # all_pairs = list(itertools.combinations(hosts, 2))
    

    # pair_index = 0
    # total_pairs = len(all_pairs)
    
    while not _stop_event.is_set():  # vong lap vo tan, den khi co lenh dung
        try:
            # Lấy danh sách tất cả hosts
            host_list = list(hosts)
            if len(host_list) < 2:
                time.sleep(1)
                continue


            # TƯ DUY MỚI: Chọn ngẫu nhiên các cặp thay vì duyệt toàn bộ
            # Tạo danh sách các cặp ngẫu nhiên cho vòng lặp này
            current_batch = []
            for _ in range(MAX_SAMPLES_PER_CYCLE):
                # Chọn 2 host ngẫu nhiên khác nhau
                src, dst = random.sample(host_list, 2)
                current_batch.append((src, dst))
            
            for h_src, h_dst in current_batch:
                if _stop_event.is_set(): break 

                pair_id = f"{h_src.name}-{h_dst.name}"
                cmd = f"ping -c 1 -W 0.1 {h_dst.IP()}" 
                
                output = ""
                try:
                    # [FIX] Thêm Lock ở đây cực kỳ quan trọng
                    # Vì lệnh Ping rất dễ bị nhiễu bởi iPerf
                    if hasattr(h_src, 'lock'):
                        with h_src.lock:
                            output = h_src.cmd(cmd)
                    else:
                        output = h_src.cmd(cmd)
                    
                    lat, loss, jit = parse_ping_output(output)
                    
                    with _cache_lock:
                        _metrics_cache[pair_id] = {
                            "latency": lat,
                            "loss": loss,
                            "jitter": jit
                        }

                except Exception as e:
                    logger.error(f"Lỗi luồng đo metrics ({pair_id}): {str(e)}")
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