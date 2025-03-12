import eventlet
eventlet.monkey_patch()  # Patch standard library for eventlet compatibility

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS
from models import (
	    active_managers,
	    managers,
	    sid_to_manager_key,
	    clients,
	    client_manager_mapping,
	    client_manager_key_mapping
	)
from config import TIMEOUT
import time
import os
import socket

# Initialize the Flask app and configure it
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize SocketIO with CORS support
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")
#socketio = SocketIO(app, async_mode="threading")  # avoid blocking

# Check if running on localhost
try:
    ip_address = socket.gethostbyname(socket.gethostname())  # This is causing the error
except socket.gaierror:
    ip_address = "127.0.0.1"  # Fallback to localhost

is_localhost = ip_address.startswith("127.") or ip_address == "localhost"

@app.route('/')
def index():
    return render_template('index.html')  # Serve the HTML page


#---------------------
# A helper function to get clients based on the manager's key
def get_clients_by_manager_key(manager_key):
    client_ids = [client_id for client_id, client_key in client_manager_key_mapping.items() if client_key == manager_key]
    client_names = [clients[client_id] for client_id in client_ids if client_id in clients]
    return client_names

@socketio.on('connect')
def on_connect():
    print(f"Client {request.sid} connected.")

@socketio.on('register_manager')
def register_manager(data):
    sid = request.sid
    timestamp = time.time()

    # Wait for timeout before allowing new connections
    if sid in active_managers and time.time() - active_managers[sid] < TIMEOUT:
        print(f"Manager {sid} is still within the timeout period.")
        return

    manager_key = data.get('key')

    if manager_key not in managers:

        if manager_key:

            # Remove old manager key mapping if present
            if sid in sid_to_manager_key and sid_to_manager_key[sid] in managers:
                old_manager_key = sid_to_manager_key[sid]
                del managers[old_manager_key]
                del sid_to_manager_key[sid]
                del active_managers[sid]

            # Register new manager
            managers[manager_key] = sid
            sid_to_manager_key[sid] = manager_key
            active_managers[sid] = timestamp

            socketio.emit('manager-message', {'message': f'You are registered with key: {manager_key}'}, room=sid)
            socketio.emit('manager-key-success', {'managerKey': manager_key}, room=sid)

            # Send client list to manager
            clients_for_manager = get_clients_by_manager_key(manager_key)
            socketio.emit('update-client-list', {'client_ids': clients_for_manager}, room=sid)
        else:
            # Handle case if no key is sent
            socketio.emit('manager-message', {'message': 'No manager key provided'}, room=sid)
    else:
        clients_for_manager = get_clients_by_manager_key(manager_key)

        socketio.emit('update-client-list', {'client_ids': clients_for_manager}, room=sid)
        #print(f"Manager with key {manager_key} already exists.")


@socketio.on('register-client')
def register_client(data):
    client_id = request.sid
    client_name = data.get('client_id')
    client_key = data.get('client_key')
    clients[client_id] = client_name
    client_manager_key_mapping[client_id] = client_key

    if client_key in managers:
        manager_sid = managers[client_key]
        client_manager_mapping[client_id] = manager_sid
        print(f"Client assign: {client_id}")
        socketio.emit('client-assigned', {'client_name': f'client_{client_id}', 'manager': manager_sid, 'client_name': client_name}, room=manager_sid)
    else:
        print(f"Client {client_id} does not match any manager's key.")

@socketio.on('send-command')
def handle_command(data):
    # Extract client_ids and miner_command from the data
    client_names = data.get('client_ids', [])  # Default to empty list if not provided
    manager_key = data.get('key', '')  # Default to empty list if not provided

    miner_command = data['miner_command']

    action = data['action']
    #print(f'action: {action}')
    # Handle the command for each client_id (example)

    if manager_key:
        valid_clients = get_clients_by_manager_key(manager_key)

        matched_clients = [client for client in client_names if client in valid_clients]
    
        if not matched_clients:
            print("No matching clients found.")
            return

        for client_name in matched_clients:
            client_id = next((key for key, value in clients.items() if value == client_name), None)

            print(f"Sending command to {client_id}: {miner_command}")
            
            if action == 1:
                print(f'action: 1')
                # Emit the command and second parameter to the specific client
                emit('execute-command', {'miner_command': miner_command}, room=client_id)
            elif action == 2:
                print(f'action: 2')
                emit('stop-command', room=client_id)

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    print(f"Client disconnect: {sid}")

    # Clean up client mappings
    if sid in clients:
        client_name = clients.pop(sid)
        manager_sid = client_manager_mapping.pop(sid, None)

        if manager_sid:
            socketio.emit('client-disconnected', {'client_name': client_name}, room=manager_sid)

    # Clean up manager mappings
    if sid in sid_to_manager_key:
        manager_key = sid_to_manager_key.pop(sid)
        managers.pop(manager_key, None)
        active_managers.pop(sid, None)

#-----------------


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))

    # Print the server port for debugging
    print(f"Server running on port: {port}")
    

    # Run the app (bind to all available IP addresses and use the dynamic port)
    if is_localhost:
        socketio.run(app, host="0.0.0.0", port=5000)
    else:
        socketio.run(app, host="0.0.0.0", port=5000, ssl_context="adhoc")

