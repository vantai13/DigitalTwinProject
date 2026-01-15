# backend/app/services/action_logger.py
"""
ACTION LOGGER SERVICE
---------------------
MỤC ĐÍCH:
- Quản lý tất cả Action Logs (CRUD operations)
- Broadcast real-time qua WebSocket
- Thread-safe (sử dụng Lock)

STORAGE:
- Phase 1: In-Memory (List) - Đơn giản, nhanh
- Phase 2: SQLite - Professional, persistent

ARCHITECTURE:
    Frontend Request
         ↓
    API Endpoint (control.py)
         ↓
    ActionLogger.create_action()  ← Tạo log PENDING
         ↓
    Emit tới Mininet
         ↓
    Nhận kết quả từ Mininet
         ↓
    ActionLogger.update_action()  ← Update SUCCESS/FAILED
         ↓
    Broadcast tới Frontend
"""

import threading
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.models.action_log import ActionLog, ActionType, ActionStatus
from app.utils.logger import get_logger

logger = get_logger()


class ActionLoggerService:
    """
    Service quản lý Action Logs
    
    THREAD-SAFE: Sử dụng threading.Lock để tránh race condition
    
    Example Usage:
    --------------
    # Khởi tạo service (singleton)
    action_logger = ActionLoggerService()
    
    # Tạo action mới
    action = action_logger.create_action(
        action_type=ActionType.TOGGLE_DEVICE,
        target="h1",
        parameters={"action": "disable"}
    )
    
    # Cập nhật kết quả thành công
    action_logger.update_action(
        action.action_id, 
        ActionStatus.SUCCESS
    )
    
    # Cập nhật kết quả thất bại
    action_logger.update_action(
        action.action_id,
        ActionStatus.FAILED,
        error_message="Device h1 not found"
    )
    
    # Lấy lịch sử
    history = action_logger.get_history(limit=10)
    """
    
    def __init__(self, socketio=None):
        """
        Khởi tạo Action Logger
        
        Args:
            socketio: Flask-SocketIO instance (để broadcast)
        """
        # Storage: In-Memory List (Phase 1)
        # Sau này sẽ thay bằng SQLite
        self._actions: List[ActionLog] = []
        
        # Lock để đảm bảo thread-safe
        self._lock = threading.Lock()
        
        # SocketIO instance để broadcast
        self.socketio = socketio
        
        logger.info(">>> ActionLoggerService initialized (In-Memory storage)")
    
    def set_socketio(self, socketio):
        """
        Set SocketIO instance sau khi khởi tạo
        (Dùng khi socketio được init sau ActionLogger)
        """
        self.socketio = socketio
        logger.info(">>> SocketIO instance attached to ActionLogger")
    
    def create_action(
        self, 
        action_type: ActionType, 
        target: str, 
        parameters: Optional[Dict[str, Any]] = None,
        user: Optional[str] = None
    ) -> ActionLog:
        """
        Tạo Action Log mới với status PENDING
        
        Args:
            action_type: Loại hành động (enum)
            target: Thiết bị/link bị tác động
            parameters: Thông số kèm theo
            user: Người thực hiện (optional)
        
        Returns:
            ActionLog: Object action mới tạo
        
        Example:
            action = action_logger.create_action(
                ActionType.TOGGLE_DEVICE,
                "h1",
                {"action": "disable"}
            )
        """
        with self._lock:
            # Tạo ActionLog object
            action = ActionLog(
                action_type=action_type,
                target=target,
                parameters=parameters,
                user=user
            )
            
            # Thêm vào storage
            self._actions.append(action)
            
            logger.info(
                f"[ActionLogger] Created: {action.action_id} | "
                f"Type: {action_type.value} | Target: {target}"
            )
            
            # Broadcast qua WebSocket (action_started event)
            self._broadcast_action(action, event_name='action_started')
            
            return action
    
    def update_action(
        self,
        action_id: str,
        status: ActionStatus,
        error_message: Optional[str] = None,
        result_data: Optional[Dict[str, Any]] = None
    ) -> Optional[ActionLog]:
        """
        Cập nhật kết quả của Action Log
        
        Args:
            action_id: ID của action cần update
            status: Trạng thái mới (SUCCESS/FAILED)
            error_message: Thông báo lỗi (nếu FAILED)
            result_data: Dữ liệu kết quả (optional)
        
        Returns:
            ActionLog or None: Action đã update, hoặc None nếu không tìm thấy
        
        Example:
            # Thành công
            action_logger.update_action(
                "act_1736612345678",
                ActionStatus.SUCCESS
            )
            
            # Thất bại
            action_logger.update_action(
                "act_1736612345679",
                ActionStatus.FAILED,
                error_message="Device h1 not found"
            )
        """
        with self._lock:
            # Tìm action trong storage
            action = self._find_action_by_id(action_id)
            
            if not action:
                logger.warning(f"[ActionLogger] Action not found: {action_id}")
                return None
            
            # Cập nhật status
            if status == ActionStatus.SUCCESS:
                action.mark_success()
            elif status == ActionStatus.FAILED:
                action.mark_failed(error_message or "Unknown error")
            
            logger.info(
                f"[ActionLogger] Updated: {action_id} | "
                f"Status: {status.value} | "
                f"Error: {error_message or 'None'}"
            )
            
            # Broadcast qua WebSocket
            event_name = 'action_completed' if status == ActionStatus.SUCCESS else 'action_failed'
            self._broadcast_action(action, event_name=event_name, result_data=result_data)
            
            return action
    
    def get_action(self, action_id: str) -> Optional[ActionLog]:
        """
        Lấy 1 action theo ID
        
        Args:
            action_id: ID của action
        
        Returns:
            ActionLog or None
        """
        with self._lock:
            return self._find_action_by_id(action_id)
    
    def get_history(
        self, 
        limit: int = 50, 
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Lấy danh sách Action Logs
        
        Args:
            limit: Số lượng actions trả về (default: 50)
            offset: Vị trí bắt đầu (default: 0)
            status_filter: Filter theo status (SUCCESS/FAILED/PENDING)
        
        Returns:
            List of action dictionaries
        
        Example:
            # Lấy 10 actions gần nhất
            history = action_logger.get_history(limit=10)
            
            # Lấy chỉ các actions thất bại
            failed_actions = action_logger.get_history(
                limit=20, 
                status_filter='FAILED'
            )
        """
        with self._lock:
            # Copy list để tránh race condition
            actions = list(self._actions)
        
        # Filter theo status nếu có
        if status_filter:
            actions = [a for a in actions if a.status == status_filter]
        
        # Sắp xếp theo thời gian (mới nhất trước)
        actions.sort(key=lambda a: a.timestamp, reverse=True)
        
        # Pagination
        paginated = actions[offset:offset + limit]
        
        # Convert sang dictionary
        return [action.to_dict() for action in paginated]
    
    def get_total_count(self, status_filter: Optional[str] = None) -> int:
        """
        Đếm tổng số actions
        
        Args:
            status_filter: Filter theo status (optional)
        
        Returns:
            int: Số lượng actions
        """
        with self._lock:
            if status_filter:
                return len([a for a in self._actions if a.status == status_filter])
            return len(self._actions)
    
    def clear_history(self):
        """
        Xóa toàn bộ lịch sử (dùng cho testing)
        
        ⚠️ DANGER: Chỉ dùng trong development/testing
        """
        with self._lock:
            self._actions.clear()
            logger.warning("[ActionLogger] History CLEARED!")
    
    # ========================================
    # PRIVATE METHODS
    # ========================================
    
    def _find_action_by_id(self, action_id: str) -> Optional[ActionLog]:
        """
        Tìm action theo ID (internal use)
        
        ⚠️ Phải gọi trong context của self._lock
        """
        for action in self._actions:
            if action.action_id == action_id:
                return action
        return None
    
    def _broadcast_action(
        self, 
        action: ActionLog, 
        event_name: str,
        result_data: Optional[Dict[str, Any]] = None
    ):
        """
        Broadcast action qua WebSocket
        
        Args:
            action: ActionLog object
            event_name: Tên event ('action_started', 'action_completed', 'action_failed')
            result_data: Dữ liệu kết quả (optional)
        """
        if not self.socketio:
            logger.debug("[ActionLogger] SocketIO not available, skip broadcast")
            return
        
        try:
            payload = action.to_dict()
            if result_data:
                payload['result'] = result_data
            
            self.socketio.emit(event_name, payload)
            logger.debug(f"[ActionLogger] Broadcasted '{event_name}': {action.action_id}")
        
        except Exception as e:
            logger.error(f"[ActionLogger] Broadcast error: {e}")


# ========================================
# SINGLETON INSTANCE
# ========================================
# Tạo instance duy nhất để dùng chung toàn app
action_logger_service = ActionLoggerService()
