# ──────────────────────────────────────────────────────────────
# logging_config.py  (tạo file riêng hoặc để ngay đầu backend.py)
# ──────────────────────────────────────────────────────────────
import logging
from logging.handlers import RotatingFileHandler
import os
import sys

def get_logger():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    LOG_DIR = os.path.join(BASE_DIR, "logs")
    os.makedirs(LOG_DIR, exist_ok=True)

    LOG_FILE = os.path.join(LOG_DIR, "backend.log")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)-8s] %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger(__name__)

    # Test ngay khi khởi tạo
    logger.info("=== BACKEND LOGGER ĐÃ KHỞI TẠO THÀNH CÔNG ===")
    return logger