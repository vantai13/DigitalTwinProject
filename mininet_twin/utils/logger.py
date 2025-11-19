import logging
import sys
import os

def setup_logger():
    """
    Thiết lập cấu hình logging:
    - Tạo thư mục logs nếu chưa có.
    - Ghi log ra file logs/mininet.log (utf-8).
    - Ghi log ra màn hình console (stdout).
    """
    # Tạo thư mục logs 
    os.makedirs("logs", exist_ok=True)

    # Cấu hình logging 
    # Kiểm tra xem logger đã có handlers chưa để tránh bị duplicate log khi import nhiều lần
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)-8s] %(message)s',
            handlers=[
                logging.FileHandler("logs/mininet.log", encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )

    logger = logging.getLogger()
    return logger