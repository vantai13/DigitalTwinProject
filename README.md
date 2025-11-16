# 🌐 Digital Twin Network Dashboard

**Real-time Digital Twin of computer networks using Mininet, Flask and Vue.js**


---

## 📋 Overview

This project creates a **real-time Digital Twin** for network topology:
- **Mininet**: Simulates real networks with hosts, switches, and links
- **Flask Backend**: The "brain" of the Digital Twin, storing and processing state
- **Vue.js Frontend**: Visual dashboard for topology and metrics
- **WebSocket**: Real-time bidirectional communication

```
┌─────────────────────┐
│  Mininet Network    │  ← Physical network (simulated)
│  (Physical Twin)    │
└──────────┬──────────┘
           │ Metrics (2s polling)
           ▼
┌─────────────────────┐
│   Flask Backend     │  ← Digital Twin "Brain"
│  + SocketIO         │     Stores Host, Switch, Link
└──────────┬──────────┘
           │ WebSocket (bidirectional)
           ▼
┌─────────────────────┐
│  Vue.js Frontend    │  ← Dashboard UI
│  + Socket.io Client │
└─────────────────────┘
```

---

## ✨ Features

### ✅ Completed
- [x] **Real-time synchronization** via WebSocket
- [x] **Dynamic topology** loaded from JSON config
- [x] **Visual status indicators**: online/offline/high-load
- [x] **Interactive graph**: Click nodes/links for details
- [x] **Animated traffic flow** on links
- [x] **Auto-reconnection** on connection loss
- [x] **Device timeout detection** (offline after 10s)
- [x] **Thread-safe operations** with locks
- [x] **Health checks** and error recovery

### 🚧 In Progress
- [ ] Latency measurement (ping-based)
- [ ] Packet loss tracking
- [ ] Historical data charts
- [ ] Export topology to PNG/JSON

### 🔮 Future Roadmap
- [ ] ML-based anomaly detection
- [ ] Network optimization suggestions
- [ ] Multi-tenancy support
- [ ] Time-series database integration (InfluxDB)
- [ ] Alert system (email/Slack)
- [ ] Custom topology editor (drag-and-drop)

---

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.8+
python3 --version

# Node.js 20+
node --version

# Mininet (on Ubuntu/Debian)
sudo apt-get update
sudo apt-get install mininet
```

### Installation

```bash
# 1. Clone repository
git clone <your-repo-url>
cd DigitalTwinProject

# 2. Setup Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Setup Frontend
cd frontend
npm install
cd ..

# 4. Create topology config (if not exists)
cat > topology.json << 'EOF'
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
EOF
```

---

## 🎮 Running the Project

### Option 1: Manual (Recommended for debugging)

**Terminal 1 - Backend:**
```bash
source venv/bin/activate
python backend/app.py
# ✓ Server starts at http://0.0.0.0:5000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
# ✓ Dashboard starts at http://localhost:5173
```

**Terminal 3 - Mininet (REQUIRES SUDO):**
```bash
# DO NOT use venv for Mininet!
sudo python3 mininet_twin/run_simulation.py
# ✓ Mininet network starts and begins sending metrics
```

### Option 2: Automated Script

```bash
chmod +x run.sh
./run.sh
```

**Note:** The script runs all components in background. Use `Ctrl+C` to stop.

---

## 📊 Architecture

### Backend (`backend/`)

```
backend/
├── app.py                    # Flask server, API endpoints, WebSocket
└── model/
    ├── host.py               # Host model (CPU, Memory)
    ├── switch.py             # Switch model (DPID, Ports)
    ├── link.py               # Link model (Throughput, Latency)
    └── network_model.py      # Manages all entities
```

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/init/topology` | Initialize entire topology |
| `POST` | `/api/update/host/<hostname>` | Update CPU/Memory of host |
| `POST` | `/api/update/link/<link_id>` | Update throughput/latency of link |
| `POST` | `/api/update/switch/<name>/heartbeat` | Switch heartbeat |
| `GET` | `/api/network/status` | Get full network snapshot |
| `GET` | `/api/health` | Health check |

**WebSocket Events:**

| Event | Direction | Description |
|-------|-----------|-------------|
| `initial_state` | Server → Client | Full topology on connect |
| `host_updated` | Server → Client | Host metrics changed |
| `switch_updated` | Server → Client | Switch status changed |
| `link_updated` | Server → Client | Link metrics changed |

### Mininet Simulation (`mininet_twin/`)

```
mininet_twin/
├── run_simulation.py      # Main loop: collect → push
├── collector.py           # Collect CPU, Memory, Network bytes
└── link_collector.py      # Calculate link throughput
```

**Sync Loop** (every 2 seconds):

1. **Collect** metrics from Mininet hosts
   - CPU: `vmstat 1 2` → parse last line
   - Memory: `free -m` → parse Mem line
   - Network bytes: `/proc/net/dev` → parse interface stats

2. **Calculate** throughput
   ```python
   delta_bytes = current_bytes - prev_bytes
   throughput_mbps = (delta_bytes * 8) / (time_interval * 1_000_000)
   ```

3. **Push** to Flask API via HTTP POST



### Frontend (`frontend/src/`)

```
frontend/src/
├── App.vue                 # Root component, WebSocket logic
├── components/
│   ├── Header.vue          # Top bar with timestamp
│   ├── TopologyView.vue    # vis-network graph
│   └── InfoPanel.vue       # Node/link detail panel
└── assets/
    └── icons/              # SVG/PNG icons
```

**Tech Stack:**
- Vue 3 Composition API
- vis-network (topology graph)
- socket.io-client (WebSocket)
- axios (HTTP client)


---

## 🔧 Configuration

### 1. Change Polling Interval

**Backend:** `backend/app.py`
```python
# Reaper thread timeout
TIMEOUT_SECONDS = 10.0  # seconds
```

**Mininet:** `mininet_twin/run_simulation.py`
```python
SYNC_INTERVAL = 2.0  # seconds
```

**Frontend:** `frontend/src/App.vue`
```javascript
// Update batch processing delay
updateTimer = setTimeout(processUpdateQueue, 50) // ms
```

### 2. Add Hosts/Switches

Edit `topology.json`:
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

### 3. Generate Traffic

In Mininet CLI:
```bash
mininet> h1 ping h2 -c 10
mininet> h1 iperf -c 10.0.0.2 -u -b 50M -t 60 &
```

### 4. Environment Variables

Create `.env` file:
```bash
# Backend
FLASK_ENV=development
LOG_LEVEL=INFO

# Mininet
API_BASE_URL=http://localhost:5000/api
SYNC_INTERVAL=2.0

# Frontend
VITE_API_URL=http://localhost:5000/api
VITE_SOCKET_URL=http://localhost:5000
```

---

## 🐛 Troubleshooting

### Backend Won't Start

**Error:** `ModuleNotFoundError: No module named 'flask'`

**Fix:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

---

### Frontend Can't Connect to Backend

**Error:** `ERR_CONNECTION_REFUSED`

**Checklist:**
1. ✅ Backend running? → `curl http://localhost:5000/api/health`
2. ✅ CORS enabled? → Check `flask-cors` installed
3. ✅ Firewall blocking port 5000? → `sudo ufw allow 5000`

---

### Mininet Not Sending Data

**Error:** Throughput always = 0

**Debug Steps:**

1. **Check interface name:**
```python
# In run_simulation.py
collector.list_all_interfaces(h1)
```

2. **Test manually:**
```bash
mininet> h1 ifconfig
mininet> h1 cat /proc/net/dev | grep h1-eth0
```

3. **Generate traffic:**
```bash
mininet> h1 iperf -c 10.0.0.2 -u -b 10M -t 999999 &
```

---

### Frontend Shows Wrong Data

**Issue:** Nodes appear offline even though Mininet is running

**Cause:** API response delayed or not arriving

**Fix:** Check Network tab in DevTools:
- Status code = 200?
- Response contains data?
- WebSocket connected?

---

## 📖 Deep Dive

### Why Digital Twin?

A **Digital Twin** is a digital replica of a physical system, synchronized in real-time.

**Use Cases:**
- **Monitoring**: Observe network state without physical access
- **Simulation**: Test "what-if" scenarios (e.g., link down, node overload)
- **Prediction**: ML models predict failures based on historical data
- **Training**: Safe environment to learn network management

### Why Throughput = (delta_bytes * 8) / interval?

```
Throughput (Mbps) = Data transferred (Megabits) / Time (seconds)

1. delta_bytes = bytes sent in time interval
2. * 8 = convert bytes → bits
3. / 1_000_000 = convert bits → megabits
4. / interval = divide by time (seconds)

Example: Send 2,000,000 bytes in 2s
→ (2,000,000 * 8) / (2 * 1,000,000) = 8 Mbps
```

### Why Sort link_id?

```python
link_id = "-".join(sorted([node1.name, node2.name]))
```

**Links are bidirectional** (2-way):
- `h1-s1` = `s1-h1` (same physical link)
- Without sorting → creates 2 separate links in Digital Twin
- With sorting → normalized to single unique ID

### Why WebSocket Instead of Polling?

**HTTP Polling:**
```
Client → [GET /api/status] → Server
Client ← [Response] ← Server
(Wait 2 seconds)
Client → [GET /api/status] → Server
...
```

**WebSocket:**
```
Client ↔ [Persistent Connection] ↔ Server
Server → [Push update] → Client (instantly!)
Server → [Push update] → Client (instantly!)
...
```

**Benefits:**
- ✅ Lower latency (no request overhead)
- ✅ Lower bandwidth (no repeated headers)
- ✅ Bidirectional (server can push)

---

## 🎯 Next Steps for Development

### Phase 1: Stability & Performance
1. **Add unit tests** for models and API
2. **Implement connection pooling** in Mininet collector
3. **Add retry logic** for failed API calls
4. **Implement graceful shutdown** for all components

### Phase 2: Enhanced Monitoring
1. **Add latency measurement** using ping
2. **Track packet loss** from iperf statistics
3. **Add switch port statistics** (bytes per port)
4. **Implement historical data storage** (SQLite/PostgreSQL)

### Phase 3: Advanced Features
1. **Add time-series charts** (Chart.js/Recharts)
2. **Implement alert system** (threshold-based)
3. **Add topology export** (PNG/JSON)
4. **Create configuration UI** (edit topology without JSON)

### Phase 4: AI/ML Integration
1. **Anomaly detection** (Isolation Forest)
2. **Traffic prediction** (LSTM)
3. **Auto-scaling suggestions** (RL agent)
4. **Root cause analysis** (causal inference)

---

## 📚 Learning Resources

### Mininet
- [Official Tutorial](http://mininet.org/walkthrough/)
- [Python API Reference](http://mininet.org/api/)

### Flask
- [Quickstart](https://flask.palletsprojects.com/quickstart/)
- [Flask-SocketIO](https://flask-socketio.readthedocs.io/)

### Vue.js
- [Vue 3 Guide](https://vuejs.org/guide/)
- [Composition API](https://vuejs.org/guide/extras/composition-api-faq.html)

### vis-network
- [Documentation](https://visjs.github.io/vis-network/docs/network/)
- [Examples](https://visjs.github.io/vis-network/examples/)

---

## 👥 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

**Coding Standards:**
- Use Python 3.8+ features (type hints, f-strings)
- Follow PEP 8 for Python
- Use ESLint for JavaScript
- Write docstrings for all functions
- Add unit tests for new features

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Mininet** - Network emulation framework
- **vis-network** - Interactive network graphs
- **Flask** - Python web framework
- **Vue.js** - Progressive JavaScript framework
- **socket.io** - Real-time communication library

---

## 📞 Contact

**Author:** Doan Van Tai

**Project Link:** [https://github.com/vantai13/DigitalTwinProject.git](https://github.com/vantai13/DigitalTwinProject.git)

---

## 🔖 Version History

### v1.0.0 (Current)
- Initial release
- Basic real-time synchronization
- Dynamic topology support
- WebSocket communication

### v0.1.0 (Beta)
- HTTP polling only
- Static topology
- Basic visualization

---

**Built with ❤️ for network engineers and researchers**