import os
import eventlet
eventlet.monkey_patch()

from dotenv import load_dotenv
from app import create_app, socketio

# Load .env
load_dotenv()

app = create_app()

if __name__ == '__main__':
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print("\n" + "="*50)
    print("FLASK BACKEND STARTING...")
    print("="*50)
    print(f"API Base URL: http://{host}:{port}/api")
    print(f"WebSocket URL: ws://{host}:{port}")
    print(f"Debug Mode: {debug}")
    print("="*50 + "\n")
    
    socketio.run(
        app,
        host=host,
        port=port,
        debug=debug,
        allow_unsafe_werkzeug=True,
        use_reloader=False
    )