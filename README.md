# 🌐 Digital Twin Network Dashboard

**Bản sao kỹ thuật số (Digital Twin) của mạng máy tính sử dụng Mininet, Flask và Vue.js**

---

## 📋 Tổng quan

Dự án này tạo một **Digital Twin** real-time cho network topology:
- **Mininet**: Mô phỏng mạng thật với hosts, switches, links
- **Flask Backend**: "Bộ não" Digital Twin, lưu trữ và xử lý trạng thái
- **Vue.js Frontend**: Dashboard trực quan hóa topology và metrics

```
┌─────────────────────┐
│  Mininet Network    │  ← Mạng vật lý (mô phỏng)
│  (Physical Twin)    │
└──────────┬──────────┘
           │ Metrics (2s polling)
           ▼
┌─────────────────────┐
│   Flask Backend     │  ← Digital Twin "Brain"
│  (NetworkModel)     │     Lưu Host, Switch, Link
└──────────┬──────────┘
           │ REST API
           ▼
┌─────────────────────┐
│  Vue.js Frontend    │  ← Dashboard UI
│  (Topology View)    │
└─────────────────────┘
```

---

## 🚀 Cài đặt nhanh

### 1. Prerequisites

```bash
# Python 3.8+
python3 --version

# Node.js 20+
node --version

# Mininet (trên Ubuntu/Debian)
sudo apt-get install mininet
```

### 2. Clone và setup

```bash
# Clone repo
git clone <your-repo-url>
cd DigitalTwinProject

# Setup Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup Frontend
cd frontend
npm install
cd ..
```

### 3. Tạo topology config

File `topology.json` (ở thư mục gốc):

```json
{
  "hosts": [
    {"name": "h1", "ip": "10.0.0.1/24", "mac": "00:00:00:00:00:01"},
    {"name": "h2", "ip": "10.0.0.2/24", "mac": "00:00:00:00:00:02"}
  ],
  "switches": [
    {"name": "s1", "dpid": "0000000000000001"}
  ],
  "links": [
    {"from": "h1", "to": "s1", "bw": 100},
    {"from": "h2", "to": "s1", "bw": 100}
  ]
}
```

---

## 🎮 Chạy dự án

### Cách 1: Chạy từng phần (Khuyến nghị cho debug)

**Terminal 1 - Backend:**
```bash
source venv/bin/activate
python backend/app.py
# ✓ Server khởi động tại http://0.0.0.0:5000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
# ✓ Dashboard khởi động tại http://localhost:5173
```

**Terminal 3 - Mininet (CẦN SUDO):**
```bash
# KHÔNG dùng venv cho Mininet!
sudo python3 mininet_twin/run_simulation.py
# ✓ Mạng Mininet khởi động và bắt đầu gửi metrics
```

### Cách 2: Chạy tự động (Script)

```bash
chmod +x run.sh
./run.sh
```

---

## 📊 Kiến trúc chi tiết

### Backend (`backend/`)

```
backend/
├── app.py              # Flask server, API endpoints
└── model/
    ├── host.py         # Host model (CPU, Memory)
    ├── switch.py       # Switch model (DPID, Ports)
    ├── link.py         # Link model (Throughput, Latency)
    └── network_model.py # Quản lý tất cả entities
```

**API Endpoints:**

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/api/update/host/<hostname>` | Update CPU/Memory của host |
| `POST` | `/api/update/link/<link_id>` | Update throughput/latency của link |
| `GET` | `/api/network/status` | Lấy snapshot toàn bộ network |
| `GET` | `/api/health` | Health check |

### Mininet Simulation (`mininet_twin/`)

```
mininet_twin/
├── run_simulation.py   # Main loop: collect → push
├── collector.py        # Thu thập CPU, Memory, Network bytes
└── topology.py         # (Reserved)
```

**Sync Loop** (mỗi 2 giây):

1. **Collect** metrics từ Mininet hosts
   - CPU: `vmstat 1 2`
   - Memory: `free -m`
   - Network bytes: `/proc/net/dev`

2. **Calculate** throughput
   ```python
   delta_bytes = current_bytes - prev_bytes
   throughput_mbps = (delta_bytes * 8) / (time_interval * 1_000_000)
   ```

3. **Push** đến Flask API qua HTTP POST

### Frontend (`frontend/src/`)

```
frontend/src/
├── App.vue             # Root component, state management
├── components/
│   ├── Header.vue      # Top bar với timestamp
│   ├── TopologyView.vue # Vis.js network diagram
│   └── InfoPanel.vue   # Chi tiết node/link đã chọn
└── assets/
    └── icons/          # SVG icons
```

**Tech stack:**
- Vue 3 Composition API
- vis-network (topology graph)
- axios (HTTP client)
- Tailwind CSS-inspired styling

---

## 🔧 Cấu hình

### 1. Thay đổi polling interval

File `mininet_twin/run_simulation.py`:
```python
SYNC_INTERVAL = 2.0  # Giây (default: 2s)
```

File `frontend/src/App.vue`:
```javascript
setInterval(fetchData, 2000) // ms (default: 2000)
```

### 2. Thêm hosts/switches

Chỉnh sửa `topology.json`:
```json
{
  "hosts": [
    {"name": "h3", "ip": "10.0.0.3/24", "mac": "00:00:00:00:00:03"}
  ],
  "switches": [
    {"name": "s2", "dpid": "0000000000000002"}
  ],
  "links": [
    {"from": "h3", "to": "s2", "bw": 100},
    {"from": "s1", "to": "s2", "bw": 1000}
  ]
}
```

### 3. Tạo traffic test

Trong Mininet CLI:
```bash
mininet> h1 ping h2 -c 10
mininet> h1 iperf -c 10.0.0.2 -u -b 50M -t 60 &
```

---

## 🐛 Troubleshooting

### Backend không khởi động

**Lỗi:** `ModuleNotFoundError: No module named 'flask'`

**Fix:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

---

### Frontend không kết nối được Backend

**Lỗi:** `ERR_CONNECTION_REFUSED`

**Checklist:**
1. ✅ Backend đang chạy? (`curl http://localhost:5000/api/health`)
2. ✅ CORS enabled? (Kiểm tra `flask-cors` đã install)
3. ✅ Firewall block port 5000?

---

### Mininet không gửi data

**Lỗi:** Throughput luôn = 0

**Debug steps:**

1. **Kiểm tra interface name:**
```python
# Trong run_simulation.py, thêm dòng này:
collector.list_all_interfaces(h1)
```

2. **Test manual:**
```bash
mininet> h1 ifconfig
mininet> h1 cat /proc/net/dev | grep h1-eth0
```

3. **Tạo traffic:**
```bash
mininet> h1 iperf -c 10.0.0.2 -u -b 10M -t 999999 &
```

---

### Frontend hiển thị sai

**Vấn đề:** Nodes bị offline dù Mininet chạy

**Nguyên nhân:** API response chưa về kịp

**Fix:** Kiểm tra Network tab trong DevTools:
- Status code = 200?
- Response có data?
- Polling interval quá ngắn?

---

## 📖 Hiểu sâu hơn

### Tại sao dùng Digital Twin?

**Digital Twin** = bản sao kỹ thuật số của hệ thống vật lý, đồng bộ real-time.

**Use cases:**
- **Monitoring**: Quan sát trạng thái network không cần truy cập vật lý
- **Simulation**: Test "what-if" scenarios (VD: link down, node overload)
- **Prediction**: ML models dự đoán failures dựa trên historical data
- **Training**: Môi trường an toàn để học network management

### Tại sao throughput = (delta_bytes * 8) / interval?

```
Throughput (Mbps) = Data transferred (Megabits) / Time (seconds)

1. delta_bytes = bytes gửi trong khoảng thời gian
2. * 8 = chuyển bytes → bits
3. / 1_000_000 = chuyển bits → megabits
4. / interval = chia cho thời gian (seconds)

VD: Gửi 2,000,000 bytes trong 2s
→ (2,000,000 * 8) / (2 * 1,000,000) = 8 Mbps
```

### Tại sao cần sort link_id?

```python
link_id = "-".join(sorted([node1.name, node2.name]))
```

**Link là bidirectional** (2 chiều):
- `h1-s1` = `s1-h1` (cùng 1 link vật lý)
- Không sort → tạo 2 link riêng biệt trong Digital Twin
- Sort → chuẩn hóa thành 1 ID duy nhất

---

## 🎯 Roadmap

### ✅ Đã hoàn thành
- [x] Basic topology visualization
- [x] Real-time metrics sync
- [x] Host/Switch/Link models
- [x] Dynamic topology from JSON

### 🚧 Đang phát triển
- [ ] Latency measurement (ping)
- [ ] Packet loss tracking
- [ ] Historical data chart
- [ ] Export topology to PNG

### 🔮 Tương lai
- [ ] ML-based anomaly detection
- [ ] Network optimization suggestions
- [ ] Multi-tenancy support
- [ ] WebSocket thay thế polling

---

## 👥 Contributors

- **Doan Van Tai** - Initial work

---

## 📄 License



---

## 🙏 Acknowledgments

- **Mininet** - Network emulation framework
- **vis-network** - Interactive network graphs
- **Flask** - Python web framework
- **Vue.js** - Progressive JavaScript framework