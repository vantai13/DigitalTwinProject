# backend/app/api/device_updates.py
from flask import Blueprint, jsonify, request
from app.extensions import digital_twin, socketio, data_lock # Import Lock để xử lý đồng bộ
from app.utils.logger import get_logger

logger = get_logger()

device_bp = Blueprint('device_updates', __name__)

# --- Helper Functions để broadcast (copy từ app.py cũ) ---
def broadcast_host_update(host_obj):
    socketio.emit('host_updated', host_obj.to_json())

def broadcast_switch_update(switch_obj):
    socketio.emit('switch_updated', switch_obj.to_json())

def broadcast_link_update(link_obj):
    socketio.emit('link_updated', link_obj.to_json())


@device_bp.route('/update/host/<hostname>', methods=['POST'])
def update_host_data(hostname): 
    """API cập nhật metrics cho Host"""
    data = request.get_json(silent=True) or {}
    
    with data_lock: 
        host_obj = digital_twin.get_host(hostname)
        if not host_obj:
            return jsonify({"status": "error", "message": "Host not found"}), 404
        
        cpu = data.get('cpu', 0.0)
        memory = data.get('memory', 0.0)
        host_obj.update_resource_metrics(cpu, memory)
        
    broadcast_host_update(host_obj)
    return jsonify({"status": "success", "message": f"{hostname} updated"})


@device_bp.route('/update/link/<link_id>', methods=['POST'])
def update_link_data(link_id):
    """API cập nhật metrics cho Link"""
    data = request.get_json(silent=True) or {}
    
    nodes = link_id.split('-')
    if len(nodes) != 2:
        return jsonify({"status": "error", "message": "Invalid Link ID"}), 400
    
    node1, node2 = nodes[0], nodes[1]
    link_obj = digital_twin.get_link(node1, node2)
    
    if not link_obj:
        return jsonify({"status": "error", "message": f"Link '{link_id}' not found"}), 404
    
    throughput = data.get('throughput', 0.0)
    latency = data.get('latency', 0.0)
    link_obj.update_performance_metrics(throughput, latency)
    
    broadcast_link_update(link_obj)
    return jsonify({"status": "success", "message": f"{link_id} updated"})


@device_bp.route('/update/switch/<switch_name>/heartbeat', methods=['POST'])
def update_switch_heartbeat(switch_name):
    """Nhận tín hiệu heartbeat từ Switch"""
    switch_obj = digital_twin.get_switch(switch_name)
    
    if not switch_obj:
        return jsonify({"status": "error", "message": "Switch not found"}), 404
    
    switch_obj.heartbeat()
    broadcast_switch_update(switch_obj)
    
    return jsonify({"status": "success"})