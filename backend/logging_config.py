# ──────────────────────────────────────────────────────────────
# logging_config.py  (tạo file riêng hoặc để ngay đầu backend.py)
# ──────────────────────────────────────────────────────────────
import logging
from logging.handlers import RotatingFileHandler
import os
import sys

def get_logger():
    os.makedirs("logs", exist_ok=True)

    # Logger cố định cho toàn bộ backend
    logger = logging.getLogger("digital_twin_backend")
    logger.setLevel(logging.INFO)

    # Nếu đã có handler rồi (khi reload module) → không tạo lại
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # ───── File handler (rotating) ─────
    file_handler = RotatingFileHandler(
        "logs/backend.log",
        maxBytes=10 * 1024 * 1024,   # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # ───── Console handler ─────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Không cho log lan lên root (tránh in 2 lần)
    logger.propagate = False

    # Test ngay khi khởi tạo
    logger.info("=== BACKEND LOGGER ĐÃ KHỞI TẠO THÀNH CÔNG ===")
    return logger