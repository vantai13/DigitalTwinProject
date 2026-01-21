
from flask import Blueprint, jsonify, request
import json
from app.extensions import digital_twin, socketio
from app.utils.logger import get_logger

logger = get_logger()

topology_bp = Blueprint('topology', __name__)

@topology_bp.route('/init/topology', methods=['POST'])
def init_topology():
    """API để Mininet gửi toàn bộ topology lên Backend"""
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400

    logger.info(">>> Nhận yêu cầu khởi tạo topology từ Mininet...")
    
    # Xóa toàn bộ topology cũ
    digital_twin.hosts.clear()
    digital_twin.switches.clear()
    digital_twin.links.clear()

    try:
        # Thêm tất cả Hosts
        for host_data in data.get('hosts', []):
            digital_twin.add_host(
                host_data['name'],
                host_data['ip'],
                host_data.get('mac', '00:00:00:00:00:00')
            )

        # Thêm tất cả Switches
        for switch_data in data.get('switches', []):
            digital_twin.add_switch(
                switch_data['name'],
                switch_data.get('dpid', '0000000000000001')
            )

        # Thêm tất cả Links
        for link_data in data.get('links', []):
            bandwidth_capacity = link_data.get('bandwidth', 100)
            if bandwidth_capacity <= 0: 
                bandwidth_capacity = 100
            digital_twin.add_link(
                link_data['node1'],
                link_data['node2'],
                bandwidth_capacity
            )

        logger.info(f">>> 'Mồi' topology thành công: {len(digital_twin.hosts)} hosts, {len(digital_twin.switches)} switches")
        
        # GỬI INITIAL STATE CHO TẤT CẢ CLIENT QUA SOCKET
        try:
            snapshot = digital_twin.get_network_snapshot()
            
            # ✅ FIX: FORCE TẤT CẢ NODES VỀ STATUS 'UP' KHI KHỞI ĐỘNG
            for node in snapshot['graph_data']['nodes']:
                if 'details' in node and 'status' in node['details']:
                    # Force status về 'up' nếu không phải 'offline'
                    if node['details']['status'] != 'offline':
                        node['details']['status'] = 'up'
                    
                    # Force group đúng
                    if node['group'] and node['group'].startswith('host'):
                        if node['details']['status'] == 'offline':
                            node['group'] = 'host-offline'
                        else:
                            node['group'] = 'host'
                    elif node['group'] and node['group'].startswith('switch'):
                        if node['details']['status'] == 'offline':
                            node['group'] = 'switch-offline'
                        else:
                            node['group'] = 'switch'
            
            socketio.emit('initial_state', snapshot)
            logger.info(">>> Đã broadcast initial_state (forced UP status) qua WebSocket")
        except Exception as emit_error:
            logger.warning(f"[CẢNH BÁO] Không thể emit WebSocket: {emit_error}")
        
        return jsonify({"status": "success", "message": "Topology initialized"})
    
    except Exception as e:
        logger.error(f"[LỖI] Init Topology: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@topology_bp.route('/network/status')
def get_network_status():
    """API endpoint để Frontend lấy snapshot"""
    snapshot = digital_twin.get_network_snapshot()
    return jsonify(snapshot)


@topology_bp.route('/health')
def health_check():
    """Kiểm tra server có sống không"""
    return jsonify({
        "status": "healthy",
        "digital_twin": digital_twin.name,
        "hosts": len(digital_twin.hosts),
        "switches": len(digital_twin.switches),
        "links": len(digital_twin.links)
    })