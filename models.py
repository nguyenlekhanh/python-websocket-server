# Models for managing clients and managers
active_managers = {}             # Store active managers
managers = {}                   # Map manager_key to sid
sid_to_manager_key = {}         # Reverse mapping: sid to manager_key
clients = {}                    # Store client details
client_manager_mapping = {}     # Map client SID to manager SID
client_manager_key_mapping = {} # Map client SID to client key
