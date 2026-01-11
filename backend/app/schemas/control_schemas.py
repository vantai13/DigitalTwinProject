# backend/app/schemas/control_schemas.py
"""
JSON SCHEMAS FOR VALIDATION
----------------------------
MỤC ĐÍCH:
- Validate dữ liệu từ Frontend TRƯỚC KHI xử lý
- Tránh lỗi runtime (vd: bandwidth = -10, delay = "abc")
- Đảm bảo dữ liệu đúng format

SỬ DỤNG:
- Import schema vào API endpoint
- Dùng hàm validate_request_data() để kiểm tra
"""

from jsonschema import validate, ValidationError


# ========================================
# SCHEMA 1: IMPORT TOPOLOGY
# ========================================
IMPORT_TOPOLOGY_SCHEMA = {
    "type": "object",
    "properties": {
        "topology": {
            "type": "object",
            "properties": {
                "hosts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "ip": {"type": "string"},  # Có thể thêm regex pattern cho IP
                            "mac": {"type": "string"}
                        },
                        "required": ["name", "ip", "mac"]
                    }
                },
                "switches": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "dpid": {"type": "string"}
                        },
                        "required": ["name", "dpid"]
                    }
                },
                "links": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "from": {"type": "string"},
                            "to": {"type": "string"},
                            "bw": {"type": "number", "minimum": 0}
                        },
                        "required": ["from", "to"]
                    }
                }
            },
            "required": ["hosts", "switches", "links"]
        }
    },
    "required": ["topology"]
}


# ========================================
# SCHEMA 2: TOGGLE DEVICE
# ========================================
TOGGLE_DEVICE_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["enable", "disable"]  # Chỉ cho phép 2 giá trị này
        }
    },
    "required": ["action"]
}


# ========================================
# SCHEMA 3: TOGGLE LINK
# ========================================
TOGGLE_LINK_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["up", "down"]
        }
    },
    "required": ["action"]
}


# ========================================
# SCHEMA 4: UPDATE LINK CONDITIONS
# ========================================
UPDATE_LINK_SCHEMA = {
    "type": "object",
    "properties": {
        "bandwidth": {
            "type": "number",
            "minimum": 0.1,  # Phải lớn hơn 0
            "description": "Bandwidth in Mbps"
        },
        "delay": {
            "type": "string",
            "pattern": "^\\d+(\\.\\d+)?(ms|us|s)$",  # Regex: "10ms", "5.5us", "1s"
            "description": "Delay với đơn vị (vd: 10ms, 500us)"
        },
        "loss": {
            "type": "number",
            "minimum": 0,
            "maximum": 100,  # % packet loss
            "description": "Packet loss percentage (0-100)"
        }
    },
    "minProperties": 1,  # Phải có ít nhất 1 trong 3 field
    "additionalProperties": False  # Không cho phép field khác
}


# ========================================
# HELPER FUNCTION: VALIDATE REQUEST DATA
# ========================================
def validate_request_data(data, schema):
    """
    Kiểm tra dữ liệu có hợp lệ theo schema không
    
    Args:
        data (dict): Dữ liệu cần validate (từ request.json)
        schema (dict): JSON schema
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    
    Example:
        is_valid, error = validate_request_data(
            request.json, 
            TOGGLE_DEVICE_SCHEMA
        )
        if not is_valid:
            return jsonify({"error": error}), 400
    """
    try:
        validate(instance=data, schema=schema)
        return True, None
    except ValidationError as e:
        # Tạo error message dễ đọc
        error_msg = f"Validation failed: {e.message}"
        if e.path:
            field_path = ".".join(str(p) for p in e.path)
            error_msg = f"Field '{field_path}': {e.message}"
        return False, error_msg


# ========================================
# DEMO: TESTING SCHEMAS
# ========================================
if __name__ == "__main__":
    print("=" * 70)
    print("TEST 1: VALID TOGGLE_DEVICE REQUEST")
    print("=" * 70)
    
    valid_data = {"action": "disable"}
    is_valid, error = validate_request_data(valid_data, TOGGLE_DEVICE_SCHEMA)
    print(f"Data: {valid_data}")
    print(f"Valid: {is_valid}, Error: {error}\n")
    
    print("=" * 70)
    print("TEST 2: INVALID TOGGLE_DEVICE REQUEST (wrong action)")
    print("=" * 70)
    
    invalid_data = {"action": "turn_off"}  # Không nằm trong enum
    is_valid, error = validate_request_data(invalid_data, TOGGLE_DEVICE_SCHEMA)
    print(f"Data: {invalid_data}")
    print(f"Valid: {is_valid}")
    print(f"Error: {error}\n")
    
    print("=" * 70)
    print("TEST 3: VALID UPDATE_LINK REQUEST")
    print("=" * 70)
    
    valid_link_data = {
        "bandwidth": 50.5,
        "delay": "10ms",
        "loss": 2.0
    }
    is_valid, error = validate_request_data(valid_link_data, UPDATE_LINK_SCHEMA)
    print(f"Data: {valid_link_data}")
    print(f"Valid: {is_valid}, Error: {error}\n")
    
    print("=" * 70)
    print("TEST 4: INVALID UPDATE_LINK REQUEST (bandwidth = 0)")
    print("=" * 70)
    
    invalid_link_data = {"bandwidth": 0}  # < 0.1
    is_valid, error = validate_request_data(invalid_link_data, UPDATE_LINK_SCHEMA)
    print(f"Data: {invalid_link_data}")
    print(f"Valid: {is_valid}")
    print(f"Error: {error}\n")
    
    print("=" * 70)
    print("TEST 5: INVALID UPDATE_LINK REQUEST (delay wrong format)")
    print("=" * 70)
    
    invalid_delay_data = {"delay": "10"}  # Thiếu đơn vị
    is_valid, error = validate_request_data(invalid_delay_data, UPDATE_LINK_SCHEMA)
    print(f"Data: {invalid_delay_data}")
    print(f"Valid: {is_valid}")
    print(f"Error: {error}\n")
    
    print("=" * 70)
    print("TEST 6: INVALID UPDATE_LINK REQUEST (loss > 100)")
    print("=" * 70)
    
    invalid_loss_data = {"loss": 150}  # Vượt quá 100%
    is_valid, error = validate_request_data(invalid_loss_data, UPDATE_LINK_SCHEMA)
    print(f"Data: {invalid_loss_data}")
    print(f"Valid: {is_valid}")
    print(f"Error: {error}\n")
    
    print("=" * 70)
    print("TEST 7: VALID IMPORT_TOPOLOGY REQUEST")
    print("=" * 70)
    
    valid_topology = {
        "topology": {
            "hosts": [
                {"name": "h1", "ip": "10.0.0.1/24", "mac": "00:00:00:00:00:01"}
            ],
            "switches": [
                {"name": "s1", "dpid": "0000000000000001"}
            ],
            "links": [
                {"from": "h1", "to": "s1", "bw": 100}
            ]
        }
    }
    is_valid, error = validate_request_data(valid_topology, IMPORT_TOPOLOGY_SCHEMA)
    print(f"Data: {valid_topology}")
    print(f"Valid: {is_valid}, Error: {error}\n")
    
    print("=" * 70)
    print("TEST 8: INVALID IMPORT_TOPOLOGY REQUEST (missing 'hosts')")
    print("=" * 70)
    
    invalid_topology = {
        "topology": {
            "switches": [{"name": "s1", "dpid": "0000000000000001"}],
            "links": []
        }
    }
    is_valid, error = validate_request_data(invalid_topology, IMPORT_TOPOLOGY_SCHEMA)
    print(f"Valid: {is_valid}")
    print(f"Error: {error}\n")