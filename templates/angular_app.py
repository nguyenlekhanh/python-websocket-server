# app.py

from flask import Flask
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return app.send_static_file('react.html')  # Serve the react HTML file

@socketio.on('connect')
def on_connect():
    print(f"Client {request.sid} connected.")
    # Emit a message to the client
    emit('manager-message', {'message': 'Hello from the server!'})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
