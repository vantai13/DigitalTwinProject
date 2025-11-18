import re  # Để parse text bằng split



def get_host_cpu_usage(host):
    """
    Lấy % CPU sử dụng nhanh hơn bằng cách dùng top chế độ batch (-b) 
    và lấy mẫu 1 lần (-n 1).
    Nhanh hơn vmstat 1 2 rất nhiều.
    """
    try:
        # Cách 1: Dùng top (khá chính xác và nhanh hơn vmstat chờ 1s)
        # grep "Cpu(s)" lấy dòng CPU, awk lấy cột idle (thường là cột 8 trong top output mặc định)
        # Output top: %Cpu(s): 10.5 us,  2.0 sy, ... 87.5 id
        # Lưu ý: Output của top có thể khác nhau tùy distro linux trong Mininet VM.
        
        # Cách an toàn hơn cho tốc độ trong Mininet giả lập:
        # Đọc /proc/loadavg để lấy load average trong 1 phút (nhanh nhất)
        # cmd_result = host.cmd("cat /proc/loadavg | awk '{print $1}'")
        # return float(cmd_result.strip()) * 10 # Hack nhẹ để hiển thị số cho đẹp nếu load thấp
        
        # HOẶC giữ nguyên vmstat NHƯNG giảm số lần lặp (nhưng vmstat < 1s không chạy được)
        # Nên ta dùng thủ thuật ps để lấy %CPU hiện tại của tiến trình (không chính xác cho toàn system nhưng nhanh)
        
        # [KHUYẾN NGHỊ] Dùng câu lệnh này để lấy CPU usage tức thời (không blocking 1s):
        # Tính toán dựa trên /proc/stat là chuẩn nhất nhưng code dài.
        # Dưới đây là cách dùng shell script ngắn gọn để tính CPU usage không delay:
        
        cmd = "grep 'cpu ' /proc/stat | awk '{usage=($2+$4)*100/($2+$4+$5)} END {print usage}'"
        cmd_result = host.cmd(cmd)
        
        return round(float(cmd_result.strip()), 2)

    except Exception as e:
        # Fallback nếu lệnh trên lỗi
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