# backend/run.py

import eventlet
eventlet.monkey_patch()
from app import create_app, socketio
# Tạo ứng dụng từ Factory
app = create_app()

if __name__ == '__main__':
    print("\n" + "="*50)
    print("FLASK BACKEND (REFACTORED) ĐANG KHỞI ĐỘNG...")
    print("="*50)
    print(f"API Base URL: http://0.0.0.0:5000/api")
    print(f"WebSocket URL: ws://0.0.0.0:5000")
    print("="*50 + "\n")
    
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=True,
        allow_unsafe_werkzeug=True,
        use_reloader=False 
    )