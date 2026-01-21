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
        
        Args:
            data (dict): {
                'device_name': 'h1',
                'action': 'enable' hoặc 'disable'
            }
        
        Returns:
            dict: Result với success/error
        """
        device_name = data.get('device_name')
        action = data.get('action')  # 'enable' hoặc 'disable'
        
        if not device_name or not action:
            return {
                'success': False,
                'error': 'Missing device_name or action'
            }
        
        # Tìm device trong Mininet
        device = self.net.get(device_name)
        
        if not device:
            return {
                'success': False,
                'error': f"Device '{device_name}' not found in Mininet"
            }
        
        try:
            # Xác định loại device (host hay switch)
            is_host = device_name.startswith('h')
            is_switch = device_name.startswith('s')
            
            if is_host:
                # ========================================
                # TOGGLE HOST
                # ========================================
                interfaces = device.intfList()

                if action == 'disable':
                    logger.info(f"[EXECUTOR] Disabling {device_name}...")
                    
                    # BƯỚC 1: KILL IPERF PROCESSES
                    try:
                        if hasattr(device, 'lock'):
                            with device.lock:
                                device.cmd('killall -9 iperf 2>/dev/null')
                                time.sleep(0.2)
                                
                                verify = device.cmd('pgrep iperf')
                                if verify.strip():
                                    logger.warning(f"[EXECUTOR] iPerf vẫn chạy trên {device_name}")
                        else:
                            device.cmd('killall -9 iperf 2>/dev/null')
                            time.sleep(0.2)
                    
                    except Exception as e:
                        logger.warning(f"[EXECUTOR] Error killing iperf: {e}")
                    
                    # BƯỚC 2: DOWN ALL INTERFACES
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
                    
                    # BƯỚC 3: VERIFY INTERFACE DOWN
                    time.sleep(0.3)
                    
                    verify_cmd = f'ip link show {interfaces[0].name}'
                    if hasattr(device, 'lock'):
                        with device.lock:
                            status = device.cmd(verify_cmd)
                    else:
                        status = device.cmd(verify_cmd)
                    
                    is_down = 'state DOWN' in status
                    
                    if is_down:
                        logger.info(f"[EXECUTOR] ✓ Host {device_name} disabled successfully")
                        message = f"Host {device_name} disabled successfully"
                    else:
                        logger.warning(f"[EXECUTOR] ⚠️ Host {device_name} may not be fully down")
                        message = f"Host {device_name} partially disabled"
                
                elif action == 'enable':
                    logger.info(f"[EXECUTOR] Enabling {device_name}...")
                    
                    # Up tất cả interfaces
                    for intf in interfaces:
                        if hasattr(device, 'lock'):
                            with device.lock:
                                device.cmd(f'ifconfig {intf.name} up')
                        else:
                            device.cmd(f'ifconfig {intf.name} up')
                    
                    # ========================================
                    # ✅ FIX: THÊM RECOVERY PROCEDURE
                    # ========================================
                    logger.info(f"[EXECUTOR] Starting recovery procedure for {device_name}...")
                    
                    # BƯỚC 1: Đợi interface lên
                    time.sleep(0.3)
                    
                    # BƯỚC 2: Flush caches
                    for intf in interfaces:
                        try:
                            if hasattr(device, 'lock'):
                                with device.lock:
                                    # Flush ARP cache
                                    device.cmd('ip neigh flush all')
                                    # Flush routing cache
                                    device.cmd('ip route flush cache')
                                    # Reset interface
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
                            logger.warning(f"[EXECUTOR] Recovery warning for {intf.name}: {e}")
                    
                    # BƯỚC 3: Đợi carrier stable
                    time.sleep(0.5)
                    
                    # BƯỚC 4: Verify carrier
                    for intf in interfaces:
                        try:
                            if hasattr(device, 'lock'):
                                with device.lock:
                                    carrier = device.cmd(f'cat /sys/class/net/{intf.name}/carrier 2>/dev/null')
                            else:
                                carrier = device.cmd(f'cat /sys/class/net/{intf.name}/carrier 2>/dev/null')
                            
                            has_carrier = '1' in carrier.strip()
                            logger.debug(f"[EXECUTOR] {device_name}-{intf.name} carrier: {has_carrier}")
                        except:
                            pass
                    
                    logger.info(f"[EXECUTOR] Host {device_name} enabled and recovered")
                    message = f"Host {device_name} enabled successfully"
                
                else:
                    return {
                        'success': False,
                        'error': f"Invalid action: {action}. Use 'enable' or 'disable'"
                    }
            
            elif is_switch:
                # ========================================
                # TOGGLE SWITCH - ✅ PHẦN NÀY QUAN TRỌNG NHẤT
                # ========================================
                if action == 'disable':
                    logger.info(f"[EXECUTOR] Disabling switch {device_name}...")
                    
                    # ✅ PRE-CLEANUP - Dọn dẹp trước khi tắt
                    try:
                        # 1. Tìm tất cả hosts kết nối với switch này
                        connected_hosts = []
                        for link in self.net.links:
                            if link.intf1.node == device or link.intf2.node == device:
                                other_node = link.intf1.node if link.intf2.node == device else link.intf2.node
                                if other_node.name.startswith('h'):
                                    connected_hosts.append(other_node)
                        
                        logger.info(f"[EXECUTOR] Found {len(connected_hosts)} hosts connected to {device_name}")
                        
                        # 2. Kill iPerf trên các hosts này
                        for h in connected_hosts:
                            try:
                                if hasattr(h, 'lock'):
                                    with h.lock:
                                        # ✅ FIX: Thêm timeout để tránh hang
                                        h.cmd('timeout 1s killall -9 iperf 2>/dev/null || true')
                                        time.sleep(0.1)
                                        # Verify kill
                                        remaining = h.cmd('pgrep iperf 2>/dev/null')
                                        if remaining.strip():
                                            logger.warning(f"[EXECUTOR] iPerf still running on {h.name}, force kill")
                                            h.cmd('pkill -9 -f iperf 2>/dev/null || true')
                                else:
                                    h.cmd('timeout 1s killall -9 iperf 2>/dev/null || true')
                                    time.sleep(0.1)
                                
                                logger.debug(f"[EXECUTOR] Killed iPerf on {h.name}")
                            except Exception as e:
                                logger.warning(f"[EXECUTOR] Error killing iPerf on {h.name}: {e}")
                        
                        # 3. Flush TC qdisc trên các interfaces
                        for h in connected_hosts:
                            try:
                                intf = h.defaultIntf()
                                if hasattr(h, 'lock'):
                                    with h.lock:
                                        h.cmd(f'tc qdisc del dev {intf.name} root 2>/dev/null')
                                else:
                                    h.cmd(f'tc qdisc del dev {intf.name} root 2>/dev/null')
                                
                                logger.debug(f"[EXECUTOR] Flushed TC on {h.name}-{intf.name}")
                            except Exception as e:
                                logger.warning(f"[EXECUTOR] Error flushing TC: {e}")
                        
                        # 4. Đợi cleanup hoàn tất
                        time.sleep(0.5)
                    
                    except Exception as e:
                        logger.error(f"[EXECUTOR] Pre-cleanup error: {e}")
                    
                    # ✅ Tắt switch với error handling
                    try:
                        device.stop()
                        logger.info(f"[EXECUTOR] Switch {device_name} stopped successfully")
                        message = f"Switch {device_name} disabled successfully"
                    except Exception as e:
                        logger.error(f"[EXECUTOR] Error stopping switch: {e}")
                        return {
                            'success': False,
                            'error': f"Failed to stop switch: {str(e)}"
                        }
                
                elif action == 'enable':
                    logger.info(f"[EXECUTOR] Enabling switch {device_name}...")
                    
                    # ✅ Bật switch với recovery procedure
                    try:
                        # 1. Start switch
                        device.start([])
                        time.sleep(0.5)
                        
                        # 2. Tìm hosts kết nối
                        connected_hosts = []
                        for link in self.net.links:
                            if link.intf1.node == device or link.intf2.node == device:
                                other_node = link.intf1.node if link.intf2.node == device else link.intf2.node
                                if other_node.name.startswith('h'):
                                    connected_hosts.append(other_node)
                        
                        # 3. Recovery procedure cho mỗi host
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
                                        
                                        verify = h.cmd(f'cat /sys/class/net/{intf.name}/carrier 2>/dev/null')
                                        has_carrier = '1' in verify
                                        logger.debug(f"[EXECUTOR] {h.name} carrier: {has_carrier}")
                                else:
                                    h.cmd('ip neigh flush all')
                                    h.cmd('ip route flush cache')
                                    h.cmd(f'ip link set {intf.name} down')
                                    time.sleep(0.1)
                                    h.cmd(f'ip link set {intf.name} up')
                            
                            except Exception as e:
                                logger.warning(f"[EXECUTOR] Recovery error for {h.name}: {e}")
                        
                        # 4. Verify switch operational
                        time.sleep(1.0)
                        flows = device.cmd('ovs-ofctl dump-flows')
                        if 'table=' in flows:
                            logger.info(f"[EXECUTOR] Switch {device_name} operational")
                            message = f"Switch {device_name} enabled successfully"
                        else:
                            logger.warning(f"[EXECUTOR] Switch {device_name} may not be fully operational")
                            message = f"Switch {device_name} enabled (verification inconclusive)"

                        # ========================================
                        # ✅ FIX: THÊM DÒNG NÀY VÀO CUỐI
                        # ========================================
                        # Đợi thêm 1s để đảm bảo hoàn toàn stable
                        time.sleep(1.0)
                        logger.info(f"[EXECUTOR] Switch {device_name} recovery completed")
                    
                    except Exception as e:
                        logger.error(f"[EXECUTOR] Error enabling switch: {e}")
                        return {
                            'success': False,
                            'error': f"Failed to enable switch: {str(e)}"
                        }
                
                else:
                    return {
                        'success': False,
                        'error': f"Invalid action: {action}. Use 'enable' or 'disable'"
                    }
            
            else:
                return {
                    'success': False,
                    'error': f"Unknown device type for '{device_name}'"
                }
            
            # Verify kết quả
            verification = None
            if is_host and action == 'enable':
                time.sleep(0.3)
                other_hosts = [h for h in self.net.hosts if h.name != device_name]
                if other_hosts:
                    target = other_hosts[0]
                    result = device.cmd(f'ping -c 1 -W 1 {target.IP()}')
                    if '1 received' in result:
                        verification = f"Verified by ping to {target.name}"
            
            return {
                'success': True,
                'message': message,
                'result': {
                    'device_name': device_name,
                    'device_type': 'host' if is_host else 'switch',
                    'action': action,
                    'verification': verification
                }
            }
        
        except Exception as e:
            logger.error(f"[EXECUTOR] Error toggling device {device_name}: {e}")
            return {
                'success': False,
                'error': f"Failed to toggle device: {str(e)}"
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


