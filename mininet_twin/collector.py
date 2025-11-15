import re  # Để parse text bằng split



def get_host_cpu_usage(host):
    """
    Lấy phần trăm (%) CPU sử dụng của một host.
    Sử dụng 'vmstat 1 2' và phân tích dòng cuối cùng.
    """
    try:
        cmd_result = host.cmd('vmstat 1 2')
        
        # Tách kết quả thành các dòng
        lines = cmd_result.strip().split('\n')
        
        # Lấy dòng cuối cùng
        last_line = lines[-1]
        
        # Tách dòng thành các "cột" (ngăn cách bởi khoảng trắng)
        # re.split(r'\s+', ...) sẽ xử lý nhiều khoảng trắng
        parts = re.split(r'\s+', last_line.strip())
        
        # Cột 'id' (idle) là cột thứ 3 từ cuối lên (index -3)
        # (hoặc cột thứ 15, index 14, nếu đếm từ trái)
        cpu_idle = float(parts[-3])
        
        # CPU Usage = 100 - CPU Idle
        cpu_usage = 100.0 - cpu_idle
        
        return round(cpu_usage, 2)
        
    except Exception as e:
        print(f"[Lỗi Collector] Không thể lấy CPU từ {host.name}: {e}")
        return 0.0

def get_host_memory_usage(host):
    """
    Lấy phần trăm (%) Memory sử dụng của một host.
    Sử dụng 'free -m' và phân tích dòng 'Mem:'.
    """
    try:
        cmd_result = host.cmd('free -m')
        
        # Tách kết quả thành các dòng
        lines = cmd_result.strip().split('\n')
        
        # Lấy dòng 'Mem:' (thường là dòng thứ 2, index 1)
        mem_line = lines[1]
        
        # Tách dòng thành các "cột"
        parts = re.split(r'\s+', mem_line.strip())
        
        # Cột 'total' là cột thứ 2 (index 1)
        # Cột 'used' là cột thứ 3 (index 2)
        mem_total = float(parts[1])
        mem_used = float(parts[2])
        
        if mem_total == 0:
            return 0.0
            
        mem_usage_percent = (mem_used / mem_total) * 100.0
        
        return round(mem_usage_percent, 2)
        
    except Exception as e:
        print(f"[Lỗi Collector] Không thể lấy Memory từ {host.name}: {e}")
        return 0.0

def get_interface_bytes(host, interface_name):
    """
    Lấy tổng số bytes TX và RX cho một interface cụ thể trên host.
    Trả về một tuple (rx_bytes, tx_bytes).
    """
    try:
        cmd_result = host.cmd(f'cat /proc/net/dev | grep {interface_name}')
        
        
        line = cmd_result.strip()
        
        # Bỏ phần 'h1-eth0:' đi
        stats = line.split(':')[1].strip()
        
        parts = re.split(r'\s+', stats)
        
        # Cột 1 (index 0) là RX bytes
        # Cột 9 (index 8) là TX bytes
        rx_bytes = int(parts[0])
        tx_bytes = int(parts[8])
        
        return rx_bytes, tx_bytes
        
    except Exception as e:
        # Lỗi này có thể xảy ra nếu interface không tồn tại
        # print(f"[Lỗi Collector] Không thể lấy bytes từ {host.name}-{interface_name}: {e}")
        return 0, 0
    
def list_all_interfaces(host):
    """Liệt kê TẤT CẢ các interface của host để debug."""
    try:
        cmd_result = host.cmd('cat /proc/net/dev')
        print(f"[DEBUG] Tất cả interface của {host.name}:")
        print(cmd_result)
    except Exception as e:
        print(f"[Lỗi] {e}")