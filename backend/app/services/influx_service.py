from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import WriteOptions
from dotenv import load_dotenv
import time
from app.utils.logger import get_logger
import os

logger = get_logger()  

load_dotenv()

class InfluxService:
    def __init__(self):
        # Load từ .env
        self.url = os.getenv('INFLUX_URL', 'http://localhost:8086')
        self.token = os.getenv('INFLUX_TOKEN', 'my-super-secret-auth-token')
        self.org = os.getenv('INFLUX_ORG', 'digitaltwin_org')
        self.bucket = os.getenv('INFLUX_BUCKET', 'network_metrics')
        
        # Write Options từ .env
        batch_size = int(os.getenv('INFLUX_BATCH_SIZE', 500))
        flush_interval = int(os.getenv('INFLUX_FLUSH_INTERVAL', 1000))
        retry_interval = int(os.getenv('INFLUX_RETRY_INTERVAL', 5000))

        self.client = None
        self.write_api = None

        try:
            self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
            self.write_api = self.client.write_api(write_options=WriteOptions(
                batch_size=batch_size,
                flush_interval=flush_interval,
                jitter_interval=0,
                retry_interval=retry_interval
            ))
            logger.info(">>> InfluxDB connected successfully!")
        except Exception as e:
            logger.error(f"InfluxDB connection error: {e}")
            self.write_api = None

    def write_telemetry_batch(self, data):
        if not self.write_api:
            return

        timestamp_sec = data.get('timestamp', time.time())
        ts_ns = int(timestamp_sec * 1_000_000_000)  

        points = []

        # ==================== 1. Host Metrics ====================
        for h in data.get('hosts', []):
            p = Point("host_metrics") \
                .tag("host_name", h.get('name', 'unknown')) \
                .field("cpu_usage", float(h.get('cpu', 0))) \
                .field("memory_usage", float(h.get('mem', 0))) \
                .time(ts_ns)
            points.append(p)

        # ==================== 2. Link Metrics ====================
        for l in data.get('links', []):
            link_id = l.get('id', 'unknown')
            parts = link_id.split('-')
            src_node = parts[0] if len(parts) >= 2 else "unknown"
            dst_node = parts[1] if len(parts) >= 2 else "unknown"

            p = Point("link_metrics") \
                .tag("link_id", link_id) \
                .tag("src_node", src_node) \
                .tag("dst_node", dst_node) \
                .field("throughput_mbps", float(l.get('bw', 0))) \
                .field("packet_loss_percent", float(l.get('loss', 0))) \
                .time(ts_ns)
            points.append(p)

        # ==================== 3. Path Latency ====================
        for lat in data.get('latency', []):
            p = Point("path_metrics") \
                .tag("pair_id", lat.get('pair', 'unknown')) \
                .field("latency_ms", float(lat.get('latency', 0))) \
                .field("packet_loss_percent", float(lat.get('loss', 0))) \
                .field("jitter_ms", float(lat.get('jitter', 0))) \
                .time(ts_ns)
            points.append(p)

        # ==================== Ghi vào InfluxDB ====================
        try:
            self.write_api.write(bucket=self.bucket, org=self.org, record=points)
            # logger.info(f"Ghi thành công {len(points)} points vào InfluxDB")
        except Exception as e:
            logger.error(f"Lỗi khi ghi InfluxDB: {e}")

    def close(self):
        if self.client:
            self.client.close()
            logger.info("InfluxDB client đã đóng.")


# Singleton instance – dùng chung toàn app
influx_service = InfluxService()