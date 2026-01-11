# 📋 API ENDPOINTS CONTRACT - BIDIRECTIONAL CONTROL

## 🎯 MỤC ĐÍCH
Document này định nghĩa **tất cả API endpoints** cho tính năng điều khiển hai chiều.
Frontend sẽ dựa vào đây để biết:
- Gọi API nào để thực hiện hành động?
- Gửi dữ liệu theo format nào?
- Nhận về response như thế nào?

---

## 🌐 **1. IMPORT TOPOLOGY MỚI**

### **Endpoint:** `POST /api/control/topology/import`

**Mục đích:** Nhập topology mới từ file JSON (thay thế toàn bộ mạng hiện tại)

**Request Body:**
```json
{
  "topology": {
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
}
```

**Success Response (200):**
```json
{
  "status": "success",
  "action_id": "act_1736612345678",
  "message": "Topology imported successfully",
  "details": {
    "hosts_added": 2,
    "switches_added": 1,
    "links_added": 2
  }
}
```

**Error Response (400/500):**
```json
{
  "status": "error",
  "action_id": "act_1736612345679",
  "message": "Invalid topology format",
  "error": "Missing required field: hosts"
}
```

---

## 🔌 **2. TOGGLE DEVICE (BẬT/TẮT HOST/SWITCH)**

### **Endpoint:** `POST /api/control/device/{device_name}/toggle`

**Mục đích:** Bật/tắt một host hoặc switch

**Path Parameter:**
- `device_name`: Tên thiết bị (vd: `h1`, `s1`)

**Request Body:**
```json
{
  "action": "enable"  // hoặc "disable"
}
```

**Success Response (200):**
```json
{
  "status": "success",
  "action_id": "act_1736612345680",
  "message": "Device h1 disabled successfully",
  "device": {
    "name": "h1",
    "status": "offline",
    "previous_status": "up"
  }
}
```

**Error Response (404):**
```json
{
  "status": "error",
  "action_id": "act_1736612345681",
  "message": "Device not found",
  "error": "Device 'h99' does not exist in Digital Twin"
}
```

---

## 🔗 **3. TOGGLE LINK (BẬT/TẮT ĐƯỜNG TRUYỀN)**

### **Endpoint:** `POST /api/control/link/{link_id}/toggle`

**Mục đích:** Bật/tắt một link (giống lệnh `net.configLinkStatus(link, 'up'/'down')`)

**Path Parameter:**
- `link_id`: ID của link (vd: `h1-s1`, thứ tự sắp xếp alphabetically)

**Request Body:**
```json
{
  "action": "up"  // hoặc "down"
}
```

**Success Response (200):**
```json
{
  "status": "success",
  "action_id": "act_1736612345682",
  "message": "Link h1-s1 set to DOWN",
  "link": {
    "id": "h1-s1",
    "status": "down",
    "previous_status": "up"
  }
}
```

---

## ⚙️ **4. UPDATE LINK CONDITIONS (THAY ĐỔI BĂNG THÔNG/DELAY/LOSS)**

### **Endpoint:** `PUT /api/control/link/{link_id}/update`

**Mục đích:** Thay đổi network conditions của link (bandwidth, delay, packet loss)

**Path Parameter:**
- `link_id`: ID của link (vd: `h1-s1`)

**Request Body:**
```json
{
  "bandwidth": 50,      // Mbps (optional, phải > 0)
  "delay": "10ms",      // String với đơn vị (optional, vd: "5ms", "100us")
  "loss": 2.0           // % packet loss (optional, 0-100)
}
```

**⚠️ VALIDATION RULES:**
- `bandwidth`: Phải là số dương (> 0)
- `delay`: Phải có đơn vị (`ms`, `us`, `s`) - vd: "10ms", "500us"
- `loss`: Phải trong khoảng 0-100 (%)

**Success Response (200):**
```json
{
  "status": "success",
  "action_id": "act_1736612345683",
  "message": "Link h1-s1 updated successfully",
  "link": {
    "id": "h1-s1",
    "bandwidth_capacity": 50,
    "delay": "10ms",
    "loss": 2.0,
    "previous_values": {
      "bandwidth_capacity": 100,
      "delay": "0ms",
      "loss": 0.0
    }
  }
}
```

**Error Response (400):**
```json
{
  "status": "error",
  "action_id": "act_1736612345684",
  "message": "Invalid parameters",
  "error": "Bandwidth must be greater than 0"
}
```

---

## 📜 **5. GET ACTION HISTORY (LẤY LỊCH SỬ HÀNH ĐỘNG)**

### **Endpoint:** `GET /api/control/actions/history`

**Mục đích:** Lấy danh sách các hành động đã thực hiện

**Query Parameters:**
- `limit` (optional): Số lượng action trả về (default: 50)
- `offset` (optional): Vị trí bắt đầu (default: 0)
- `status` (optional): Filter theo status (`SUCCESS`, `FAILED`, `PENDING`)

**Example Request:**
```
GET /api/control/actions/history?limit=10&status=FAILED
```

**Success Response (200):**
```json
{
  "status": "success",
  "total": 123,
  "limit": 10,
  "offset": 0,
  "actions": [
    {
      "action_id": "act_1736612345685",
      "timestamp": "2025-01-11T10:30:15.123456",
      "action_type": "TOGGLE_DEVICE",
      "target": "h1",
      "parameters": {"action": "disable"},
      "status": "FAILED",
      "error_message": "Host h1 is already offline",
      "user": null,
      "completed_at": "2025-01-11T10:30:15.456789"
    },
    {
      "action_id": "act_1736612345686",
      "timestamp": "2025-01-11T10:29:00.123456",
      "action_type": "UPDATE_LINK",
      "target": "h1-s1",
      "parameters": {"bandwidth": 50, "delay": "10ms"},
      "status": "SUCCESS",
      "error_message": null,
      "user": null,
      "completed_at": "2025-01-11T10:29:00.789012"
    }
  ]
}
```

---

## 🔌 **WEBSOCKET EVENTS**

### **1. Client → Backend (Frontend gửi lệnh)**

#### Event: `control_request`
```json
{
  "action_type": "TOGGLE_DEVICE",
  "target": "h1",
  "parameters": {"action": "disable"}
}
```

---

### **2. Backend → Client (Backend thông báo)**

#### Event: `action_started`
**Phát khi bắt đầu xử lý hành động**
```json
{
  "action_id": "act_1736612345687",
  "action_type": "TOGGLE_DEVICE",
  "target": "h1",
  "status": "PENDING"
}
```

#### Event: `action_completed`
**Phát khi hành động hoàn thành thành công**
```json
{
  "action_id": "act_1736612345687",
  "action_type": "TOGGLE_DEVICE",
  "target": "h1",
  "status": "SUCCESS",
  "message": "Device h1 disabled successfully",
  "result": {
    "name": "h1",
    "status": "offline"
  }
}
```

#### Event: `action_failed`
**Phát khi hành động thất bại**
```json
{
  "action_id": "act_1736612345688",
  "action_type": "UPDATE_LINK",
  "target": "h1-s99",
  "status": "FAILED",
  "error_message": "Link h1-s99 does not exist"
}
```

---

## 🔐 **AUTHENTICATION (OPTIONAL - PHASE 2)**

Hiện tại **KHÔNG CÓ authentication**. Tất cả requests đều được chấp nhận.

**Future Enhancement:**
- Thêm JWT token authentication
- Phân quyền theo role (Admin, Viewer)
- Lưu `user` field trong ActionLog

---

## 📊 **STATUS CODES**

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Request thành công |
| 400 | Bad Request | Dữ liệu không hợp lệ (validation failed) |
| 404 | Not Found | Device/Link không tồn tại |
| 500 | Internal Server Error | Lỗi server (bug, Mininet crash...) |

---

## 🧪 **TESTING CHECKLIST**

### **Bước 1: Test với cURL**
```bash
# Test 1: Toggle device
curl -X POST http://localhost:5000/api/control/device/h1/toggle \
  -H "Content-Type: application/json" \
  -d '{"action": "disable"}'

# Test 2: Update link
curl -X PUT http://localhost:5000/api/control/link/h1-s1/update \
  -H "Content-Type: application/json" \
  -d '{"bandwidth": 50, "delay": "10ms", "loss": 2.0}'

# Test 3: Get history
curl http://localhost:5000/api/control/actions/history?limit=5
```

### **Bước 2: Test với Postman/Insomnia**
Import các endpoints và test từng cái một

### **Bước 3: Test với Frontend**
Tạo UI buttons để gọi các API này

---

## 📝 **NOTES**

1. **Link ID Format:** Luôn sắp xếp alphabetically (`h1-s1`, KHÔNG phải `s1-h1`)
2. **Timestamps:** Sử dụng ISO 8601 format (`2025-01-11T10:30:15.123456`)
3. **Error Handling:** Luôn trả về `action_id` kể cả khi thất bại (để trace lỗi)
4. **Idempotency:** Gọi API 2 lần với cùng tham số phải cho kết quả giống nhau

---

**📅 Version:** 1.0  
**👤 Author:** Digital Twin Team  
**📆 Last Updated:** 2025-01-11