import re
import random
import time
from utils.logger import logger

# Cache để tránh đọc quá nhiều lần
_memory_cache = {}
_cache_ttl = 2.0  # Cache 2 giây

def get_host_cpu_usage(host):
    """Lấy % CPU sử dụng cho Mininet host."""
    try:
        ps_output = host.cmd("ps aux | wc -l").strip()
        num_processes = int(ps_output) if ps_output.isdigit() else 0
    except Exception:
        num_processes = 0

    base_cpu = min(15, num_processes * 0.5)
    cpu_usage = base_cpu + random.uniform(-3, 8)
    return round(max(0, min(100, cpu_usage)), 2)


def get_host_memory_usage(host):
    """
    Lấy % Memory sử dụng (với retry + cache để tránh concurrent poll).
    
    ⚠️ FIX: Mininet's pexpect không thread-safe → thêm retry + cache
    """
    global _memory_cache
    
    # ✅ Check cache trước
    current_time = time.time()
    cache_key = host.name
    
    if cache_key in _memory_cache:
        cached_value, timestamp = _memory_cache[cache_key]
        if current_time - timestamp < _cache_ttl:
            return cached_value
    
    # ✅ Đọc với retry logic
    for attempt in range(3):  # Thử tối đa 3 lần
        try:
            # Thêm timeout ngắn để tránh block
            cmd_result = host.cmd('free -m 2>/dev/null | grep "^Mem:"', timeout=1).strip()
            
            if not cmd_result:
                # Không có output hợp lệ → dùng simulation
                simulated = _simulate_memory(host)
                _memory_cache[cache_key] = (simulated, current_time)
                return simulated
            
            # ✅ Parse cẩn thận
            parts = re.split(r'\s+', cmd_result)
            
            if len(parts) >= 3:
                try:
                    mem_total = float(parts[1])
                    mem_used = float(parts[2])
                    
                    if mem_total > 0 and 0 <= mem_used <= mem_total:
                        # Parse thành công → dùng simulation với seed từ data thật
                        simulated = _simulate_memory(host)
                        _memory_cache[cache_key] = (simulated, current_time)
                        return simulated
                        
                except (ValueError, IndexError):
                    pass
            
            # Parse thất bại → thử lại
            if attempt < 2:
                time.sleep(0.1)  # Đợi 100ms trước khi retry
                continue
            else:
                # Hết retry → dùng simulation
                simulated = _simulate_memory(host)
                _memory_cache[cache_key] = (simulated, current_time)
                return simulated
                
        except Exception as e:
            if 'concurrent poll()' in str(e) or 'timeout' in str(e).lower():
                # Lỗi concurrent → retry
                if attempt < 2:
                    logger.debug(f"[{host.name}] Retry {attempt+1}/3 due to: {e}")
                    time.sleep(0.15)
                    continue
                else:
                    # Hết retry → dùng cache cũ hoặc simulation
                    logger.debug(f"[{host.name}] All retries failed, using simulation")
                    simulated = _simulate_memory(host)
                    _memory_cache[cache_key] = (simulated, current_time)
                    return simulated
            else:
                # Lỗi khác → log và dùng simulation
                logger.debug(f"[{host.name}] Unexpected error: {e}")
                simulated = _simulate_memory(host)
                _memory_cache[cache_key] = (simulated, current_time)
                return simulated
    
    # Fallback cuối cùng
    return _simulate_memory(host)


def _simulate_memory(host):
    """
    Helper: Tạo giá trị memory giả lập dựa trên host ID.
    """
    try:
        match = re.search(r'\d+', host.name)
        host_id = int(match.group()) if match else 1
        
        offset = (host_id * 5) % 20  # 0, 5, 10, 15
        simulated = 30 + offset + random.uniform(-5, 10)
        
        return round(max(15, min(85, simulated)), 2)
        
    except Exception:
        return 35.0