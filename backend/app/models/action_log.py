# backend/app/models/action_log.py
"""
MODEL: Action Log
-----------------
MỤC ĐÍCH: 
- Lưu lại mọi hành động điều khiển (bật/tắt device, thay đổi bandwidth...)
- Giống như "nhật ký" ghi lại ai đã làm gì, lúc nào, thành công hay thất bại

CẤU TRÚC DỮ LIỆU:
- action_id: ID duy nhất (vd: "act_1234567890")
- timestamp: Thời gian thực hiện (ISO format)
- action_type: Loại hành động (IMPORT_TOPOLOGY, TOGGLE_DEVICE, TOGGLE_LINK, UPDATE_LINK)
- target: Thiết bị/link bị tác động (vd: "h1", "s1-s2")
- parameters: Thông số (dict) - vd: {"bandwidth": 50, "delay": "10ms"}
- status: Trạng thái (SUCCESS, FAILED, PENDING)
- error_message: Thông báo lỗi (nếu thất bại)
- user: Người thực hiện (optional - để sau này thêm authentication)
"""

import time
from datetime import datetime
from enum import Enum


class ActionType(Enum):
    """Các loại hành động có thể thực hiện"""
    IMPORT_TOPOLOGY = "IMPORT_TOPOLOGY"       # Nhập topology mới từ JSON
    TOGGLE_DEVICE = "TOGGLE_DEVICE"           # Bật/tắt host hoặc switch
    TOGGLE_LINK = "TOGGLE_LINK"               # Bật/tắt link
    UPDATE_LINK = "UPDATE_LINK"               # Thay đổi bandwidth/delay/loss của link


class ActionStatus(Enum):
    """Trạng thái của hành động"""
    PENDING = "PENDING"       # Đang chờ xử lý
    SUCCESS = "SUCCESS"       # Thành công
    FAILED = "FAILED"         # Thất bại


class ActionLog:
    """
    Class đại diện cho 1 hành động điều khiển
    
    VÍ DỤ SỬ DỤNG:
    --------------
    # Tạo action mới
    action = ActionLog(
        action_type=ActionType.TOGGLE_DEVICE,
        target="h1",
        parameters={"action": "disable"}
    )
    
    # Cập nhật kết quả
    action.mark_success()
    # hoặc
    action.mark_failed("Host h1 không tồn tại")
    
    # Chuyển thành JSON để gửi cho Frontend
    action_dict = action.to_dict()
    """
    
    def __init__(self, action_type, target, parameters=None, user=None):
        """
        Khởi tạo Action Log mới
        
        Args:
            action_type (ActionType): Loại hành động (enum)
            target (str): Thiết bị/link bị tác động (vd: "h1", "s1-s2")
            parameters (dict): Thông số kèm theo (vd: {"bandwidth": 50})
            user (str): Người thực hiện (optional)
        """
        self.action_id = f"act_{int(time.time() * 1000)}"  # ID duy nhất dựa trên timestamp
        self.timestamp = datetime.now().isoformat()         # Thời gian tạo (ISO 8601)
        self.action_type = action_type.value                # Loại hành động (string)
        self.target = target                                # Thiết bị/link
        self.parameters = parameters or {}                  # Thông số (dict rỗng nếu không có)
        self.status = ActionStatus.PENDING.value            # Mặc định là PENDING
        self.error_message = None                           # Chưa có lỗi
        self.user = user                                    # Người thực hiện (None nếu không có)
        self.completed_at = None                            # Thời gian hoàn thành (sẽ set sau)
    
    def mark_success(self):
        """Đánh dấu hành động thành công"""
        self.status = ActionStatus.SUCCESS.value
        self.completed_at = datetime.now().isoformat()
        self.error_message = None
    
    def mark_failed(self, error_message):
        """
        Đánh dấu hành động thất bại
        
        Args:
            error_message (str): Thông báo lỗi
        """
        self.status = ActionStatus.FAILED.value
        self.completed_at = datetime.now().isoformat()
        self.error_message = error_message
    
    def to_dict(self):
        """
        Chuyển object thành dictionary (để gửi qua API/WebSocket)
        
        Returns:
            dict: Dictionary chứa toàn bộ thông tin
        """
        return {
            "action_id": self.action_id,
            "timestamp": self.timestamp,
            "action_type": self.action_type,
            "target": self.target,
            "parameters": self.parameters,
            "status": self.status,
            "error_message": self.error_message,
            "user": self.user,
            "completed_at": self.completed_at
        }
    
    def __repr__(self):
        """String representation cho debug"""
        return (f"ActionLog(id={self.action_id}, type={self.action_type}, "
                f"target={self.target}, status={self.status})")


