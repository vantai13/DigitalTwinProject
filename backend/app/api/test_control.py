# backend/app/api/test_control.py
"""
TEST ENDPOINTS - Dùng để test ActionLogger
-------------------------------------------
⚠️ CHỈ DÙNG TRONG DEVELOPMENT
Sẽ xóa sau khi hoàn thành tính năng thực tế
"""

from flask import Blueprint, jsonify, request
from app.extensions import action_logger_service
from app.models.action_log import ActionType, ActionStatus
from app.utils.logger import get_logger
import time

logger = get_logger()

test_control_bp = Blueprint('test_control', __name__)


@test_control_bp.route('/test/action/create', methods=['POST'])
def test_create_action():
    """
    Test endpoint để tạo action
    
    Example Request:
        POST /api/test/action/create
        {
            "action_type": "TOGGLE_DEVICE",
            "target": "h1",
            "parameters": {"action": "disable"}
        }
    """
    data = request.get_json() or {}
    
    try:
        action_type_str = data.get('action_type', 'TOGGLE_DEVICE')
        action_type = ActionType[action_type_str]  # Convert string to enum
        
        target = data.get('target', 'h1')
        parameters = data.get('parameters', {})
        
        # Tạo action
        action = action_logger_service.create_action(
            action_type=action_type,
            target=target,
            parameters=parameters
        )
        
        logger.info(f"[TEST] Created action: {action.action_id}")
        
        return jsonify({
            "status": "success",
            "message": "Action created",
            "action": action.to_dict()
        }), 201
    
    except Exception as e:
        logger.error(f"[TEST] Error creating action: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@test_control_bp.route('/test/action/<action_id>/complete', methods=['POST'])
def test_complete_action(action_id):
    """
    Test endpoint để mark action SUCCESS/FAILED
    
    Example Request:
        POST /api/test/action/act_123456/complete
        {
            "status": "SUCCESS"  // hoặc "FAILED"
            "error_message": "Something went wrong"  // optional
        }
    """
    data = request.get_json() or {}
    
    try:
        status_str = data.get('status', 'SUCCESS')
        status = ActionStatus[status_str]
        
        error_message = data.get('error_message')
        
        # Update action
        action = action_logger_service.update_action(
            action_id=action_id,
            status=status,
            error_message=error_message
        )
        
        if not action:
            return jsonify({
                "status": "error",
                "message": f"Action {action_id} not found"
            }), 404
        
        logger.info(f"[TEST] Updated action: {action_id} → {status_str}")
        
        return jsonify({
            "status": "success",
            "message": f"Action marked as {status_str}",
            "action": action.to_dict()
        })
    
    except Exception as e:
        logger.error(f"[TEST] Error updating action: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@test_control_bp.route('/test/action/history', methods=['GET'])
def test_get_history():
    """
    Test endpoint để lấy lịch sử actions
    
    Example Request:
        GET /api/test/action/history?limit=10&status=FAILED
    """
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        status_filter = request.args.get('status')  # SUCCESS, FAILED, PENDING
        
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
    
    except Exception as e:
        logger.error(f"[TEST] Error getting history: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@test_control_bp.route('/test/action/simulate', methods=['POST'])
def test_simulate_action():
    """
    Test endpoint mô phỏng toàn bộ flow:
    1. Tạo action (PENDING)
    2. Giả lập xử lý (sleep 2s)
    3. Mark SUCCESS/FAILED ngẫu nhiên
    
    Example Request:
        POST /api/test/action/simulate
        {
            "action_type": "UPDATE_LINK",
            "target": "h1-s1",
            "parameters": {"bandwidth": 50}
        }
    """
    data = request.get_json() or {}
    
    try:
        action_type_str = data.get('action_type', 'TOGGLE_DEVICE')
        action_type = ActionType[action_type_str]
        
        target = data.get('target', 'h1')
        parameters = data.get('parameters', {})
        
        # STEP 1: Tạo action
        action = action_logger_service.create_action(
            action_type=action_type,
            target=target,
            parameters=parameters
        )
        
        logger.info(f"[TEST SIMULATE] Step 1: Created {action.action_id}")
        
        # STEP 2: Giả lập xử lý (trong thực tế, đây là lúc gửi lệnh tới Mininet)
        import random
        time.sleep(2)  # Giả lập delay
        
        # STEP 3: Random SUCCESS/FAILED
        if random.random() > 0.3:  # 70% thành công
            action_logger_service.update_action(
                action.action_id,
                ActionStatus.SUCCESS
            )
            logger.info(f"[TEST SIMULATE] Step 3: SUCCESS")
        else:
            action_logger_service.update_action(
                action.action_id,
                ActionStatus.FAILED,
                error_message="Simulated random failure"
            )
            logger.info(f"[TEST SIMULATE] Step 3: FAILED")
        
        # Lấy action đã update
        updated_action = action_logger_service.get_action(action.action_id)
        
        return jsonify({
            "status": "success",
            "message": "Action simulated",
            "action": updated_action.to_dict()
        })
    
    except Exception as e:
        logger.error(f"[TEST] Error simulating action: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@test_control_bp.route('/test/action/clear', methods=['POST'])
def test_clear_history():
    """
    ⚠️ DANGER: Xóa toàn bộ lịch sử actions
    
    CHỈ DÙNG TRONG TESTING!
    """
    try:
        action_logger_service.clear_history()
        
        logger.warning("[TEST] Action history CLEARED!")
        
        return jsonify({
            "status": "success",
            "message": "All actions cleared"
        })
    
    except Exception as e:
        logger.error(f"[TEST] Error clearing history: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500