# mininet_twin/controllers/command_executor.py
"""
MININET COMMAND EXECUTOR
------------------------
MỤC ĐÍCH:
- Nhận lệnh điều khiển từ Backend qua WebSocket
- Thực thi lệnh trên Mininet network
- Trả kết quả về Backend (success/failed)

COMMANDS SUPPORTED:
1. reload_topology: Reload toàn bộ mạng từ JSON
2. toggle_device: Bật/tắt host hoặc switch
3. toggle_link: Bật/tắt link
4. update_link_conditions: Thay đổi bandwidth/delay/loss

ARCHITECTURE:
    Backend (WebSocket)
         ↓
    execute_command event
         ↓
    CommandExecutor.execute()
         ↓
    Mininet API / tc commands
         ↓
    Return result
"""

import time
import re
from utils.logger import setup_logger

logger = setup_logger()


class CommandExecutor:
    """
    Class thực thi lệnh điều khiển trên Mininet
    
    Example Usage:
    --------------
    executor = CommandExecutor(net)
    
    result = executor.execute({
        'action_id': 'act_123',
        'command': 'toggle_device',
        'data': {
            'device_name': 'h1',
            'action': 'disable'
        }
    })
    
    if result['success']:
        print("Command executed successfully!")
    else:
        print(f"Error: {result['error']}")
    """
    
    def __init__(self, net):
        """
        Khởi tạo Command Executor
        
        Args:
            net: Mininet network instance
        """
        self.net = net
        logger.info(">>> CommandExecutor initialized")
    
    def execute(self, command_data):
        """
        Thực thi lệnh dựa trên command type
        
        Args:
            command_data (dict): {
                'action_id': 'act_123...',
                'command': 'toggle_device',
                'data': {...}
            }
        
        Returns:
            dict: {
                'success': True/False,
                'action_id': 'act_123...',
                'command': 'toggle_device',
                'message': 'Success message',
                'error': 'Error message (nếu failed)',
                'result': {...}  # Dữ liệu kết quả (optional)
            }
        """
        action_id = command_data.get('action_id', 'unknown')
        command = command_data.get('command')
        data = command_data.get('data', {})
        
        logger.info(f"[EXECUTOR] Executing command: {command} | Action: {action_id}")
        
        try:
            # Routing commands
            if command == 'reload_topology':
                result = self._reload_topology(data)
            elif command == 'toggle_device':
                result = self._toggle_device(data)
            elif command == 'toggle_link':
                result = self._toggle_link(data)
            elif command == 'update_link_conditions':
                result = self._update_link_conditions(data)
            else:
                return {
                    'success': False,
                    'action_id': action_id,
                    'command': command,
                    'error': f"Unknown command: {command}"
                }
            
            # Add metadata
            result['action_id'] = action_id
            result['command'] = command
            
            return result
        
        except Exception as e:
            logger.error(f"[EXECUTOR] Error executing {command}: {e}", exc_info=True)
            return {
                'success': False,
                'action_id': action_id,
                'command': command,
                'error': str(e)
            }
    
    # ========================================
    # COMMAND IMPLEMENTATIONS
    # ========================================
    
    def _reload_topology(self, data):
        """
        Reload toàn bộ topology từ JSON
        
        Args:
            data (dict): {
                'topology': {
                    'hosts': [...],
                    'switches': [...],
                    'links': [...]
                }
            }
        
        Returns:
            dict: Result với success/error
        
        ⚠️ WARNING: Tính năng này phức tạp, cần:
        - Stop net hiện tại
        - Parse JSON → Rebuild topology
        - Start net mới
        - Re-establish WebSocket connections
        
        TODO: Implement sau khi các tính năng khác hoạt động ổn định
        """
        return {
            'success': False,
            'message': 'Reload topology not implemented yet',
            'error': 'This feature requires stopping and restarting Mininet'
        }
    
    def _toggle_device(self, data):
        """
        Bật/tắt một host hoặc switch
        
        ✅ FIX: Thêm force update về Backend sau khi toggle
        """
        device_name = data.get('device_name')
        action = data.get('action')
        
        if not device_name or not action:
            return {
                'success': False,
                'error': 'Missing device_name or action'
            }
        
        device = self.net.get(device_name)
        
        if not device:
            return {
                'success': False,
                'error': f"Device '{device_name}' not found in Mininet"
            }
        
        try:
            is_host = device_name.startswith('h')
            is_switch = device_name.startswith('s')
            
            if is_host:
                # ========================================
                # HOST TOGGLE
                # ========================================
                interfaces = device.intfList()

                if action == 'disable':
                    logger.info(f"[EXECUTOR] Disabling {device_name}...")
                    
                    # Kill iPerf
                    try:
                        if hasattr(device, 'lock'):
                            with device.lock:
                                device.cmd('killall -9 iperf 2>/dev/null')
                                time.sleep(0.2)
                        else:
                            device.cmd('killall -9 iperf 2>/dev/null')
                            time.sleep(0.2)
                    except Exception as e:
                        logger.warning(f"[EXECUTOR] Error killing iperf: {e}")
                    
                    # Down interfaces
                    for intf in interfaces:
                        try:
                            if hasattr(device, 'lock'):
                                with device.lock:
                                    device.cmd(f'ifconfig {intf.name} down')
                                    device.cmd(f'tc qdisc del dev {intf.name} root 2>/dev/null')
                            else:
                                device.cmd(f'ifconfig {intf.name} down')
                                device.cmd(f'tc qdisc del dev {intf.name} root 2>/dev/null')
                        except Exception as e:
                            logger.error(f"[EXECUTOR] Error disabling {intf.name}: {e}")
                    
                    time.sleep(0.3)
                    message = f"Host {device_name} disabled successfully"
                
                elif action == 'enable':
                    logger.info(f"[EXECUTOR] Enabling {device_name}...")
                    
                    # Up interfaces
                    for intf in interfaces:
                        if hasattr(device, 'lock'):
                            with device.lock:
                                device.cmd(f'ifconfig {intf.name} up')
                        else:
                            device.cmd(f'ifconfig {intf.name} up')
                    
                    # Recovery procedure
                    time.sleep(0.3)
                    
                    for intf in interfaces:
                        try:
                            if hasattr(device, 'lock'):
                                with device.lock:
                                    device.cmd('ip neigh flush all')
                                    device.cmd('ip route flush cache')
                                    device.cmd(f'ip link set {intf.name} down')
                                    time.sleep(0.1)
                                    device.cmd(f'ip link set {intf.name} up')
                            else:
                                device.cmd('ip neigh flush all')
                                device.cmd('ip route flush cache')
                                device.cmd(f'ip link set {intf.name} down')
                                time.sleep(0.1)
                                device.cmd(f'ip link set {intf.name} up')
                        except Exception as e:
                            logger.warning(f"[EXECUTOR] Recovery warning: {e}")
                    
                    time.sleep(0.5)
                    message = f"Host {device_name} enabled successfully"
                    
                    # ========================================
                    # ✅ FIX 1: GỬI STATUS UPDATE NGAY LẬP TỨC
                    # ========================================
                    self._send_device_status_update(device_name, 'up', is_host=True)
                
                else:
                    return {
                        'success': False,
                        'error': f"Invalid action: {action}"
                    }
            
            elif is_switch:
                # ========================================
                # SWITCH TOGGLE
                # ========================================
                if action == 'disable':
                    logger.info(f"[EXECUTOR] Disabling switch {device_name}...")
                    
                    # Pre-cleanup
                    try:
                        connected_hosts = []
                        for link in self.net.links:
                            if link.intf1.node == device or link.intf2.node == device:
                                other_node = link.intf1.node if link.intf2.node == device else link.intf2.node
                                if other_node.name.startswith('h'):
                                    connected_hosts.append(other_node)
                        
                        logger.info(f"[EXECUTOR] Found {len(connected_hosts)} hosts connected")
                        
                        for h in connected_hosts:
                            try:
                                if hasattr(h, 'lock'):
                                    with h.lock:
                                        h.cmd('timeout 1s killall -9 iperf 2>/dev/null || true')
                                        time.sleep(0.1)
                                else:
                                    h.cmd('timeout 1s killall -9 iperf 2>/dev/null || true')
                                    time.sleep(0.1)
                            except Exception as e:
                                logger.warning(f"[EXECUTOR] Error: {e}")
                        
                        time.sleep(0.5)
                    
                    except Exception as e:
                        logger.error(f"[EXECUTOR] Pre-cleanup error: {e}")
                    
                    # Stop switch
                    device.stop()
                    logger.info(f"[EXECUTOR] Switch {device_name} stopped")
                    message = f"Switch {device_name} disabled successfully"
                    
                    # ========================================
                    # ✅ FIX 2: GỬI STATUS UPDATE CHO SWITCH
                    # ========================================
                    self._send_device_status_update(device_name, 'offline', is_host=False)
                
                elif action == 'enable':
                    logger.info(f"[EXECUTOR] Enabling switch {device_name}...")
                    
                    # Start switch
                    device.start([])
                    time.sleep(0.5)
                    
                    # Recovery
                    connected_hosts = []
                    for link in self.net.links:
                        if link.intf1.node == device or link.intf2.node == device:
                            other_node = link.intf1.node if link.intf2.node == device else link.intf2.node
                            if other_node.name.startswith('h'):
                                connected_hosts.append(other_node)
                    
                    for h in connected_hosts:
                        try:
                            intf = h.defaultIntf()
                            if hasattr(h, 'lock'):
                                with h.lock:
                                    h.cmd('ip neigh flush all')
                                    h.cmd('ip route flush cache')
                                    h.cmd(f'ip link set {intf.name} down')
                                    time.sleep(0.1)
                                    h.cmd(f'ip link set {intf.name} up')
                            else:
                                h.cmd('ip neigh flush all')
                                h.cmd('ip route flush cache')
                                h.cmd(f'ip link set {intf.name} down')
                                time.sleep(0.1)
                                h.cmd(f'ip link set {intf.name} up')
                        except Exception as e:
                            logger.warning(f"[EXECUTOR] Recovery error: {e}")
                    
                    time.sleep(1.0)
                    message = f"Switch {device_name} enabled successfully"
                    
                    # ========================================
                    # ✅ FIX 3: GỬI STATUS UPDATE CHO SWITCH
                    # ========================================
                    self._send_device_status_update(device_name, 'up', is_host=False)
                
                else:
                    return {
                        'success': False,
                        'error': f"Invalid action: {action}"
                    }
            
            else:
                return {
                    'success': False,
                    'error': f"Unknown device type"
                }
            
            return {
                'success': True,
                'message': message,
                'result': {
                    'device_name': device_name,
                    'device_type': 'host' if is_host else 'switch',
                    'action': action
                }
            }
        
        except Exception as e:
            logger.error(f"[EXECUTOR] Error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _toggle_link(self, data):
        """
        Bật/tắt một link
        
        Args:
            data (dict): {
                'link_id': 'h1-s1',
                'node1': 'h1',
                'node2': 's1',
                'action': 'up' hoặc 'down'
            }
        
        Returns:
            dict: Result với success/error
        """
        link_id = data.get('link_id')
        node1_name = data.get('node1')
        node2_name = data.get('node2')
        action = data.get('action')  # 'up' hoặc 'down'
        
        if not all([link_id, node1_name, node2_name, action]):
            return {
                'success': False,
                'error': 'Missing link_id, node1, node2, or action'
            }
        
        try:
            # Lấy nodes từ Mininet
            node1 = self.net.get(node1_name)
            node2 = self.net.get(node2_name)
            
            if not node1 or not node2:
                return {
                    'success': False,
                    'error': f"Node not found: {node1_name} or {node2_name}"
                }
            
            # Tìm link giữa 2 nodes
            links = self.net.linksBetween(node1, node2)
            
            if not links:
                return {
                    'success': False,
                    'error': f"No link found between {node1_name} and {node2_name}"
                }
            
            link = links[0]  # Lấy link đầu tiên (thường chỉ có 1)
            
            # ========================================
            # SỬ DỤNG MININET API: configLinkStatus
            # ========================================
            if action == 'down':
                self.net.configLinkStatus(node1_name, node2_name, 'down')
                logger.info(f"[EXECUTOR] Link {link_id} set to DOWN")
                message = f"Link {link_id} disabled successfully"
            
            elif action == 'up':
                self.net.configLinkStatus(node1_name, node2_name, 'up')
                logger.info(f"[EXECUTOR] Link {link_id} set to UP")
                message = f"Link {link_id} enabled successfully"
            
            else:
                return {
                    'success': False,
                    'error': f"Invalid action: {action}. Use 'up' or 'down'"
                }
            
            # Verify bằng cách check interface status
            time.sleep(0.1)  # Wait cho command apply
            
            # Lấy interface từ một trong 2 nodes
            intf = link.intf1 if link.intf1.node == node1 else link.intf2
            verify_cmd = f'ip link show {intf.name}'
            
            if hasattr(intf.node, 'lock'):
                with intf.node.lock:
                    status_output = intf.node.cmd(verify_cmd)
            else:
                status_output = intf.node.cmd(verify_cmd)
            
            is_up = 'state UP' in status_output
            
            return {
                'success': True,
                'message': message,
                'result': {
                    'link_id': link_id,
                    'node1': node1_name,
                    'node2': node2_name,
                    'action': action,
                    'verified_status': 'up' if is_up else 'down'
                }
            }
        
        except Exception as e:
            logger.error(f"[EXECUTOR] Error toggling link {link_id}: {e}")
            return {
                'success': False,
                'error': f"Failed to toggle link: {str(e)}"
            }
    
    def _update_link_conditions(self, data):
        """
        Thay đổi network conditions của link (bandwidth, delay, loss)
        
        Args:
            data (dict): {
                'link_id': 'h1-s1',
                'node1': 'h1',
                'node2': 's1',
                'conditions': {
                    'bandwidth': 50,      # Mbps (optional)
                    'delay': '10ms',      # String với đơn vị (optional)
                    'loss': 2.0           # % (optional)
                }
            }
        
        Returns:
            dict: Result với success/error
        """
        link_id = data.get('link_id')
        node1_name = data.get('node1')
        node2_name = data.get('node2')
        conditions = data.get('conditions', {})
        
        if not all([link_id, node1_name, node2_name]):
            return {
                'success': False,
                'error': 'Missing link_id, node1, or node2'
            }
        
        if not conditions:
            return {
                'success': False,
                'error': 'No conditions provided'
            }
        
        try:
            # Lấy nodes từ Mininet
            node1 = self.net.get(node1_name)
            node2 = self.net.get(node2_name)
            
            if not node1 or not node2:
                return {
                    'success': False,
                    'error': f"Node not found: {node1_name} or {node2_name}"
                }
            
            # Tìm link
            links = self.net.linksBetween(node1, node2)
            
            if not links:
                return {
                    'success': False,
                    'error': f"No link found between {node1_name} and {node2_name}"
                }
            
            link = links[0]
            
            # ========================================
            # SỬ DỤNG MININET TCIntf.config()
            # ========================================
            # Lấy interface (thường config trên cả 2 interfaces)
            intf1 = link.intf1
            intf2 = link.intf2
            
            # Chuẩn bị parameters cho config
            config_params = {}
            
            if 'bandwidth' in conditions:
                bw = conditions['bandwidth']
                if bw <= 0:
                    return {
                        'success': False,
                        'error': 'Bandwidth must be greater than 0'
                    }
                config_params['bw'] = bw
            
            if 'delay' in conditions:
                delay = conditions['delay']
                # Validate delay format (phải có đơn vị: ms, us, s)
                if not re.match(r'^\d+(\.\d+)?(ms|us|s)$', delay):
                    return {
                        'success': False,
                        'error': f"Invalid delay format: {delay}. Use format like '10ms', '500us'"
                    }
                config_params['delay'] = delay
            
            if 'loss' in conditions:
                loss = conditions['loss']
                if not (0 <= loss <= 100):
                    return {
                        'success': False,
                        'error': 'Packet loss must be between 0 and 100%'
                    }
                config_params['loss'] = loss
            
            # Apply config to both interfaces
            logger.info(f"[EXECUTOR] Applying config to {link_id}: {config_params}")
            
            # Config intf1
            try:
                intf1.config(**config_params)
            except Exception as e:
                logger.warning(f"[EXECUTOR] Error configuring {intf1.name}: {e}")
            
            # Config intf2 (symmetric)
            try:
                intf2.config(**config_params)
            except Exception as e:
                logger.warning(f"[EXECUTOR] Error configuring {intf2.name}: {e}")
            
            logger.info(f"[EXECUTOR] Link {link_id} conditions updated successfully")
            
            return {
                'success': True,
                'message': f"Link {link_id} conditions updated successfully",
                'result': {
                    'link_id': link_id,
                    'node1': node1_name,
                    'node2': node2_name,
                    'applied_conditions': config_params
                }
            }
        
        except Exception as e:
            logger.error(f"[EXECUTOR] Error updating link conditions {link_id}: {e}")
            return {
                'success': False,
                'error': f"Failed to update link conditions: {str(e)}"
            }
        
    # ========================================
    # ✅ HÀM MỚI: GỬI STATUS UPDATE
    # ========================================
    def _send_device_status_update(self, device_name, status, is_host=True):
        """
        Gửi status update trực tiếp về Backend qua SocketIO
        
        Args:
            device_name (str): Tên thiết bị (h1, s1...)
            status (str): 'up', 'offline', 'down'
            is_host (bool): True nếu là host, False nếu là switch
        """
        try:
            # Import socket_client (nếu chưa có)
            from services.socket_client import socket_client_instance
            
            if not socket_client_instance:
                logger.warning(f"[EXECUTOR] SocketClient not available, skip status update")
                return
            
            if not socket_client_instance.is_connected():
                logger.warning(f"[EXECUTOR] Socket not connected, skip status update")
                return
            
            # Tạo update data
            if is_host:
                update_data = {
                    'name': device_name,
                    'status': status,
                    'cpu_utilization': 0.0 if status == 'offline' else None,
                    'memory_usage': 0.0 if status == 'offline' else None
                }
                event_name = 'host_updated'
            else:
                update_data = {
                    'name': device_name,
                    'status': status
                }
                event_name = 'switch_updated'
            
            # Gửi qua socket
            socket_client_instance.sio.emit(event_name, update_data)
            logger.info(f"[EXECUTOR] ✓ Sent {event_name}: {device_name} -> {status}")
        
        except Exception as e:
            logger.error(f"[EXECUTOR] Error sending status update: {e}")


