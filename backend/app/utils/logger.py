# backend/app/utils/logger.py
import logging
import os
import sys

def get_logger():
    """
    Cấu hình Logger để ghi log ra file logs/backend.log ở thư mục gốc dự án.
    """
    # 1. Xác định thư mục gốc dự án (Root Project)
    # File này đang ở: .../backend/app/utils/logger.py
    # Cần đi ngược lên 4 cấp để ra Root: utils -> app -> backend -> Root
    
    current_dir = os.path.dirname(os.path.abspath(__file__)) # .../backend/app/utils
    backend_app_dir = os.path.dirname(current_dir)           # .../backend/app
    backend_dir = os.path.dirname(backend_app_dir)           # .../backend
    root_dir = os.path.dirname(backend_dir)                  # .../DigitalTwinProject (Root)
    
    BASE_DIR = root_dir

    # 2. Tạo thư mục logs ở Root nếu chưa có
    LOG_DIR = os.path.join(BASE_DIR, "logs")
    os.makedirs(LOG_DIR, exist_ok=True)

    LOG_FILE = os.path.join(LOG_DIR, "backend.log")

    # 3. Cấu hình logging
    # Kiểm tra để tránh add handler nhiều lần nếu gọi hàm này nhiều lần
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)-8s] %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )

    logger = logging.getLogger("DigitalTwinBackend")
    logger.setLevel(logging.INFO)

    # logger.info("=== BACKEND LOGGER ĐÃ KHỞI TẠO (Utils) ===")
    return logger