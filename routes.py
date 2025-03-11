------------ not working when moving socket to here -------------------------

from flask import Flask, render_template, request, jsonify
from app import socketio
from flask_socketio import emit, join_room
from models import active_managers, managers, sid_to_manager_key, clients, client_manager_mapping, client_manager_key_mapping
from config import TIMEOUT
import time

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
    print(f"connect 111111111")
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
        socketio.emit('client-assigned', {'client_name': f'client_{client_id}', 'manager': manager_sid, 'client_name': client_name}, room=manager_sid)
    else:
        print(f"Client {client_id} does not match any manager's key.")

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid

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
