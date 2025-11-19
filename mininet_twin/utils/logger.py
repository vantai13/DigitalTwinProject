import logging
import sys
import os

def setup_logger():
    # Tạo thư mục logs ở cấp cha của thư mục hiện tại
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    log_dir = os.path.join(project_root, "logs")
    os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)-8s] %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "mininet.log"), encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("MininetTwin")

# Tạo sẵn một instance để các module khác import dùng luôn
logger = setup_logger()