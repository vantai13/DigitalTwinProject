# backend/app/api/control.py
"""
CONTROL API ENDPOINTS
---------------------
MỤC ĐÍCH:
- Cung cấp REST API để Frontend điều khiển Digital Twin
- Validate dữ liệu đầu vào
- Tạo Action Log và broadcast qua WebSocket
- Gửi lệnh tới Mininet (sẽ thực hiện ở Bước 4-5)

FLOW:
1. Frontend gửi request → API endpoint
2. Validate dữ liệu (JSON Schema)
3. Tạo Action Log (status=PENDING)
4. [TODO] Gửi lệnh tới Mininet qua WebSocket
5. Return ngay cho Frontend (non-blocking)
6. [TODO] Khi Mininet trả kết quả → Update Action Log → Broadcast
"""

from flask import Blueprint, jsonify, request
from app.extensions import digital_twin, socketio, data_lock, action_logger_service
from app.models.action_log import ActionType, ActionStatus
from app.schemas.control_schemas import (
    IMPORT_TOPOLOGY_SCHEMA,
    TOGGLE_DEVICE_SCHEMA,
    TOGGLE_LINK_SCHEMA,
    UPDATE_LINK_SCHEMA,
    validate_request_data
)
from app.utils.logger import get_logger

logger = get_logger()

control_bp = Blueprint('control', __name__)


# ========================================
# 1. IMPORT TOPOLOGY
# ========================================
@control_bp.route('/control/topology/import', methods=['POST'])
def import_topology():
    """
    Nhập topology mới từ JSON (thay thế toàn bộ mạng hiện tại)
    
    Request Body:
        {
            "topology": {
                "hosts": [...],
                "switches": [...],
                "links": [...]
            }
        }
    
    Response (200):
        {
            "status": "success",
            "action_id": "act_123...",
            "message": "Topology import initiated",
            "details": {
                "hosts_count": 5,
                "switches_count": 2,
                "links_count": 7
            }
        }
    """
    data = request.get_json(silent=True)
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "No JSON data provided"
        }), 400
    
    # STEP 1: Validate schema
    is_valid, error = validate_request_data(data, IMPORT_TOPOLOGY_SCHEMA)
    if not is_valid:
        logger.warning(f"[CONTROL] Import topology validation failed: {error}")
        return jsonify({
            "status": "error",
            "message": "Invalid topology format",
            "error": error
        }), 400
    
    topology = data['topology']
    
    # STEP 2: Tạo Action Log
    action = action_logger_service.create_action(
        action_type=ActionType.IMPORT_TOPOLOGY,
        target="topology.json",
        parameters={
            "hosts_count": len(topology.get('hosts', [])),
            "switches_count": len(topology.get('switches', [])),
            "links_count": len(topology.get('links', []))
        }
    )
    
    logger.info(f"[CONTROL] Import topology action created: {action.action_id}")
    
    # STEP 3: [TODO] Gửi lệnh tới Mininet (phức tạp, implement sau)
    # Hiện tại chỉ log action, không thực hiện reload
    logger.warning(f"[CONTROL] Import topology not implemented yet: {action.action_id}")
    
    # STEP 5: Return ngay (non-blocking)
    return jsonify({
        "status": "success",
        "action_id": action.action_id,
        "message": "Topology import initiated",
        "details": {
            "hosts_count": len(topology.get('hosts', [])),
            "switches_count": len(topology.get('switches', [])),
            "links_count": len(topology.get('links', []))
        }
    }), 202  # 202 Accepted (đang xử lý)


# ========================================
# 2. TOGGLE DEVICE (BẬT/TẮT HOST/SWITCH)
# ========================================
@control_bp.route('/control/device/<device_name>/toggle', methods=['POST'])
def toggle_device(device_name):
    """
    Bật/tắt một host hoặc switch
    
    Path Parameter:
        device_name: Tên thiết bị (vd: h1, s1)
    
    Request Body:
        {
            "action": "enable"  // hoặc "disable"
        }
    
    Response (200):
        {
            "status": "success",
            "action_id": "act_123...",
            "message": "Device h1 toggle initiated",
            "device": {
                "name": "h1",
                "current_status": "up",
                "requested_action": "disable"
            }
        }
    """
    data = request.get_json(silent=True)
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "No JSON data provided"
        }), 400
    
    # STEP 1: Validate schema
    is_valid, error = validate_request_data(data, TOGGLE_DEVICE_SCHEMA)
    if not is_valid:
        return jsonify({
            "status": "error",
            "message": "Invalid request data",
            "error": error
        }), 400
    
    requested_action = data['action']  # "enable" hoặc "disable"
    
    # STEP 2: Kiểm tra device tồn tại trong Digital Twin
    with data_lock:
        # Tìm trong hosts
        device = digital_twin.get_host(device_name)
        device_type = "host"
        
        # Nếu không phải host, tìm trong switches
        if not device:
            device = digital_twin.get_switch(device_name)
            device_type = "switch"
        
        if not device:
            logger.warning(f"[CONTROL] Device not found: {device_name}")
            return jsonify({
                "status": "error",
                "message": f"Device '{device_name}' not found in Digital Twin"
            }), 404
        
        current_status = device.status
    
    # STEP 3: Tạo Action Log
    action = action_logger_service.create_action(
        action_type=ActionType.TOGGLE_DEVICE,
        target=device_name,
        parameters={
            "action": requested_action,
            "device_type": device_type,
            "current_status": current_status
        }
    )
    
    logger.info(
        f"[CONTROL] Toggle device action created: {action.action_id} | "
        f"Device: {device_name} | Action: {requested_action}"
    )
    
    # STEP 4: Gửi lệnh tới Mininet qua WebSocket
    socketio.emit('execute_command', {
        'action_id': action.action_id,
        'command': 'toggle_device',
        'data': {
            'device_name': device_name,
            'action': requested_action
        }
    })
    
    logger.info(f"[CONTROL] Command sent to Mininet: toggle_device | Action: {action.action_id}")
    
    # STEP 6: Return ngay
    return jsonify({
        "status": "success",
        "action_id": action.action_id,
        "message": f"Device {device_name} toggle initiated",
        "device": {
            "name": device_name,
            "type": device_type,
            "current_status": current_status,
            "requested_action": requested_action
        }
    }), 202


# ========================================
# 3. TOGGLE LINK (BẬT/TẮT ĐƯỜNG TRUYỀN)
# ========================================
@control_bp.route('/control/link/<link_id>/toggle', methods=['POST'])
def toggle_link(link_id):
    """
    Bật/tắt một link
    
    Path Parameter:
        link_id: ID của link (vd: h1-s1, phải sorted alphabetically)
    
    Request Body:
        {
            "action": "up"  // hoặc "down"
        }
    
    Response (200):
        {
            "status": "success",
            "action_id": "act_123...",
            "message": "Link h1-s1 toggle initiated",
            "link": {
                "id": "h1-s1",
                "current_status": "up",
                "requested_action": "down"
            }
        }
    """
    data = request.get_json(silent=True)
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "No JSON data provided"
        }), 400
    
    # STEP 1: Validate schema
    is_valid, error = validate_request_data(data, TOGGLE_LINK_SCHEMA)
    if not is_valid:
        return jsonify({
            "status": "error",
            "message": "Invalid request data",
            "error": error
        }), 400
    
    requested_action = data['action']  # "up" hoặc "down"
    
    # STEP 2: Parse link_id và kiểm tra tồn tại
    parts = link_id.split('-')
    if len(parts) != 2:
        return jsonify({
            "status": "error",
            "message": "Invalid link_id format. Expected: 'node1-node2'"
        }), 400
    
    node1, node2 = parts[0], parts[1]
    
    with data_lock:
        link = digital_twin.get_link(node1, node2)
        
        if not link:
            logger.warning(f"[CONTROL] Link not found: {link_id}")
            return jsonify({
                "status": "error",
                "message": f"Link '{link_id}' not found in Digital Twin"
            }), 404
        
        current_status = link.status
    
    # STEP 3: Tạo Action Log
    action = action_logger_service.create_action(
        action_type=ActionType.TOGGLE_LINK,
        target=link_id,
        parameters={
            "action": requested_action,
            "current_status": current_status
        }
    )
    
    logger.info(
        f"[CONTROL] Toggle link action created: {action.action_id} | "
        f"Link: {link_id} | Action: {requested_action}"
    )
    
    # STEP 4: Gửi lệnh tới Mininet qua WebSocket
    socketio.emit('execute_command', {
        'action_id': action.action_id,
        'command': 'toggle_link',
        'data': {
            'link_id': link_id,
            'node1': node1,
            'node2': node2,
            'action': requested_action
        }
    })
    
    logger.info(f"[CONTROL] Command sent to Mininet: toggle_link | Action: {action.action_id}")
    
    # STEP 6: Return ngay
    return jsonify({
        "status": "success",
        "action_id": action.action_id,
        "message": f"Link {link_id} toggle initiated",
        "link": {
            "id": link_id,
            "current_status": current_status,
            "requested_action": requested_action
        }
    }), 202


# ========================================
# 4. UPDATE LINK CONDITIONS
# ========================================
@control_bp.route('/control/link/<link_id>/update', methods=['PUT'])
def update_link_conditions(link_id):
    """
    Thay đổi network conditions của link (bandwidth, delay, packet loss)
    
    Path Parameter:
        link_id: ID của link (vd: h1-s1)
    
    Request Body:
        {
            "bandwidth": 50,      // Mbps (optional)
            "delay": "10ms",      // String với đơn vị (optional)
            "loss": 2.0           // % packet loss (optional)
        }
    
    Response (200):
        {
            "status": "success",
            "action_id": "act_123...",
            "message": "Link h1-s1 update initiated",
            "link": {
                "id": "h1-s1",
                "current_conditions": {...},
                "requested_conditions": {...}
            }
        }
    """
    data = request.get_json(silent=True)
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "No JSON data provided"
        }), 400
    
    # STEP 1: Validate schema
    is_valid, error = validate_request_data(data, UPDATE_LINK_SCHEMA)
    if not is_valid:
        return jsonify({
            "status": "error",
            "message": "Invalid request data",
            "error": error
        }), 400
    
    # STEP 2: Parse link_id và kiểm tra tồn tại
    parts = link_id.split('-')
    if len(parts) != 2:
        return jsonify({
            "status": "error",
            "message": "Invalid link_id format. Expected: 'node1-node2'"
        }), 400
    
    node1, node2 = parts[0], parts[1]
    
    with data_lock:
        link = digital_twin.get_link(node1, node2)
        
        if not link:
            logger.warning(f"[CONTROL] Link not found: {link_id}")
            return jsonify({
                "status": "error",
                "message": f"Link '{link_id}' not found in Digital Twin"
            }), 404
        
        # Lưu giá trị hiện tại
        current_conditions = {
            "bandwidth": link.bandwidth_capacity,
            "delay": "0ms",  # TODO: Lưu delay trong Link model
            "loss": 0.0      # TODO: Lưu loss trong Link model
        }
    
    # Lấy giá trị mới từ request
    requested_conditions = {}
    if 'bandwidth' in data:
        requested_conditions['bandwidth'] = data['bandwidth']
    if 'delay' in data:
        requested_conditions['delay'] = data['delay']
    if 'loss' in data:
        requested_conditions['loss'] = data['loss']
    
    # STEP 3: Tạo Action Log
    action = action_logger_service.create_action(
        action_type=ActionType.UPDATE_LINK,
        target=link_id,
        parameters={
            "current_conditions": current_conditions,
            "requested_conditions": requested_conditions
        }
    )
    
    logger.info(
        f"[CONTROL] Update link action created: {action.action_id} | "
        f"Link: {link_id} | Conditions: {requested_conditions}"
    )
    
    # STEP 4: Gửi lệnh tới Mininet qua WebSocket
    socketio.emit('execute_command', {
        'action_id': action.action_id,
        'command': 'update_link_conditions',
        'data': {
            'link_id': link_id,
            'node1': node1,
            'node2': node2,
            'conditions': requested_conditions
        }
    })
    
    logger.info(f"[CONTROL] Command sent to Mininet: update_link_conditions | Action: {action.action_id}")
    
    # STEP 6: Return ngay
    return jsonify({
        "status": "success",
        "action_id": action.action_id,
        "message": f"Link {link_id} update initiated",
        "link": {
            "id": link_id,
            "current_conditions": current_conditions,
            "requested_conditions": requested_conditions
        }
    }), 202


# ========================================
# 5. GET ACTION HISTORY
# ========================================
@control_bp.route('/control/actions/history', methods=['GET'])
def get_action_history():
    """
    Lấy danh sách các hành động đã thực hiện
    
    Query Parameters:
        limit (int): Số lượng actions trả về (default: 50)
        offset (int): Vị trí bắt đầu (default: 0)
        status (str): Filter theo status (SUCCESS, FAILED, PENDING)
    
    Example Request:
        GET /api/control/actions/history?limit=10&status=FAILED
    
    Response (200):
        {
            "status": "success",
            "total": 123,
            "limit": 10,
            "offset": 0,
            "actions": [...]
        }
    """
    try:
        # Parse query parameters
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        status_filter = request.args.get('status')  # SUCCESS, FAILED, PENDING
        
        # Validate limit (tránh request quá lớn)
        if limit > 200:
            limit = 200
        
        if limit < 1:
            limit = 1
        
        # Lấy history từ ActionLogger
        history = action_logger_service.get_history(
            limit=limit,
            offset=offset,
            status_filter=status_filter
        )
        
        total = action_logger_service.get_total_count(status_filter)
        
        return jsonify({
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "actions": history
        })
    
    except ValueError as e:
        return jsonify({
            "status": "error",
            "message": "Invalid query parameters",
            "error": str(e)
        }), 400
    
    except Exception as e:
        logger.error(f"[CONTROL] Error getting action history: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500


# ========================================
# 6. HEALTH CHECK
# ========================================
@control_bp.route('/control/health', methods=['GET'])
def control_health():
    """
    Kiểm tra Control API có hoạt động không
    
    Response (200):
        {
            "status": "healthy",
            "message": "Control API is operational",
            "statistics": {
                "total_actions": 123,
                "pending_actions": 5,
                "success_actions": 100,
                "failed_actions": 18
            }
        }
    """
    try:
        stats = {
            "total_actions": action_logger_service.get_total_count(),
            "pending_actions": action_logger_service.get_total_count('PENDING'),
            "success_actions": action_logger_service.get_total_count('SUCCESS'),
            "failed_actions": action_logger_service.get_total_count('FAILED')
        }
        
        return jsonify({
            "status": "healthy",
            "message": "Control API is operational",
            "statistics": stats
        })
    
    except Exception as e:
        logger.error(f"[CONTROL] Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "message": str(e)
        }), 500