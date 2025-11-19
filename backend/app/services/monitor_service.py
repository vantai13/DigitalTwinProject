# backend/app/services/monitor_service.py
import threading
import time
from datetime import datetime, timedelta
from app.extensions import digital_twin, data_lock, socketio
from app.utils.logger import get_logger

logger = get_logger()

# --- Helper Functions để broadcast (Viết lại gọn ở đây để dùng nội bộ) ---
def broadcast_update(event_name, data_json):
    try:
        socketio.emit(event_name, data_json)
    except Exception as e:
        logger.error(f"Lỗi broadcast {event_name}: {e}")

def check_device_status_loop():
    """Kiểm tra thiết bị timeout"""
    TIMEOUT_SECONDS = 6
    logger.info(f" Kiểm tra thiết bị mỗi 3 giây (Timeout: {TIMEOUT_SECONDS}s)")

    while True:
        try:
            time.sleep(3) 
            with data_lock:
                now = datetime.now()
                timeout_threshold = timedelta(seconds=TIMEOUT_SECONDS)

                # 1. Kiểm tra Hosts
                for host in digital_twin.hosts.values():
                    if host.last_update_time:
                        if (now - host.last_update_time) > timeout_threshold:
                            if host.status != 'offline':
                                logger.warning(f"[Reaper] Host {host.name} timeout → OFFLINE")
                                host.set_status('offline')
                                broadcast_update('host_updated', host.to_json())

                # 2. Kiểm tra Switches
                for switch in digital_twin.switches.values():
                    if switch.last_update_time:
                        if (now - switch.last_update_time) > timeout_threshold:
                            if switch.status != 'offline':
                                logger.warning(f"[Reaper] Switch {switch.name} timeout → OFFLINE")
                                switch.set_status('offline')
                                broadcast_update('switch_updated', switch.to_json())

                # 3. Kiểm tra Links
                for link in digital_twin.links.values():
                    if link.last_update_time:
                        if (now - link.last_update_time) > timeout_threshold:
                            if link.status != 'down':
                                logger.warning(f"[Reaper] Link {link.id} timeout → DOWN")
                                link.set_status('down')
                                broadcast_update('link_updated', link.to_json())

        except Exception as e:
            logger.error(f"[Reaper Lỗi] {e}")

def start_monitoring_service():
    """Hàm khởi động thread, sẽ được gọi ở __init__.py"""
    reaper_thread = threading.Thread(target=check_device_status_loop, daemon=True)
    reaper_thread.start()
    logger.info(">>> Đã khởi động Monitoring Service (Reaper Thread)")