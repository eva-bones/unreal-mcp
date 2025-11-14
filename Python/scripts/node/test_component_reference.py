#!/usr/bin/env python
"""
Test script for component reference in blueprints via MCP.
This tests the fix for the component reference node issue.
"""
import random
import string
import sys
import os
import time
import socket
import json
import logging
from typing import Dict, Any, Optional

# Add the parent directory to the path so we can import the server module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestComponentReference")

random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=3))

def send_command(sock: socket.socket, command: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Send a command to the Unreal MCP server and get the response."""
    try:
        # Create command object
        command_obj = {
            "type": command,
            "params": params
        }
        
        # Convert to JSON and send
        command_json = json.dumps(command_obj)
        logger.info(f"Sending command: {command_json}")
        sock.sendall(command_json.encode('utf-8'))
        
        # Receive response
        chunks = []
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
            
            # Try parsing to see if we have a complete response
            try:
                data = b''.join(chunks)
                json.loads(data.decode('utf-8'))
                # If we can parse it, we have the complete response
                break
            except json.JSONDecodeError:
                # Not a complete JSON object yet, continue receiving
                continue
        
        # Parse response
        data = b''.join(chunks)
        response = json.loads(data.decode('utf-8'))
        logger.info(f"Received response: {response}")
        return response
        
    except Exception as e:
        logger.error(f"Error sending command: {e}")
        return None

def main():
    """Test component reference node creation and connection."""
    try:
        # Connect to the server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 55557))
        
        # Step 1: Create a blueprint
        bp_params = {
            "name": "TestCompRefBP_"+random_suffix,
            "parent_class": "Actor"
        }
        
        response = send_command(sock, "create_blueprint", bp_params)
        if not response or response.get("status") != "success":
            logger.error(f"Failed to create blueprint: {response}")
            return
        
        logger.info("Blueprint created successfully!")
        
        # Step 2: Add a static mesh component
        component_params = {
            "blueprint_name": "TestCompRefBP_"+random_suffix,
            "component_type": "/Script/Engine.StaticMeshComponent",
            "component_name": "TestMesh",
            "location": [0.0, 0.0, 0.0],
            "rotation": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0]
        }
        
        sock.close()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 55557))
        
        response = send_command(sock, "add_component_to_blueprint", component_params)
        if not response or response.get("status") != "success":
            logger.error(f"Failed to add component: {response}")
            return
            
        logger.info("Static mesh component added successfully!")



        sock.close()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 55557))

        logger.info("Setting static mesh for the new component...")
        mesh_params = {
            "blueprint_name": "TestCompRefBP_"+random_suffix,  # Use the same blueprint name variable
            "component_name": "TestMesh",
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }

        response = send_command(sock, "set_static_mesh_properties", mesh_params)

        if not response or response.get("status") != "success":
            logger.error(f"Failed to set static mesh properties: {response}")
            return

        logger.info("Static mesh properties set successfully!")

        sock.close()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 55557))

        logger.info("Enabling physics for the new component...")
        physics_params = {
            "blueprint_name": "TestCompRefBP_"+random_suffix,  # Use the same blueprint name variable
            "component_name": "TestMesh",
            "simulate_physics": True,
            "gravity_enabled": True
        }

        response = send_command(sock, "set_physics_properties", physics_params)

        if not response or response.get("status") != "success":
            logger.error(f"Failed to set physics properties: {response}")
            return

        logger.info("Physics properties set successfully!")

        # Step 3: Add an event (BeginPlay)
        sock.close()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 55557))
        
        begin_play_params = {
            "blueprint_name": "TestCompRefBP_"+random_suffix,
            "event_name": "ReceiveBeginPlay",
            "node_position": [0, 0]
        }
        
        response = send_command(sock, "add_blueprint_event_node", begin_play_params)
        if not response or response.get("status") != "success":
            logger.error(f"Failed to add BeginPlay event: {response}")
            return
            
        begin_play_node_id = response.get("result", {}).get("node_id")
        logger.info(f"BeginPlay event node added successfully with ID: {begin_play_node_id}")

        # Step 5: Add AddForce function node
        sock.close()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 55557))

        function_params = {
            "blueprint_name": "TestCompRefBP_"+random_suffix,
            "function_name": "AddForce",  # The function we want to call
            "target": "TestMesh",  # The component we want to call it on
            "params": {
                "Force": [0, 0, 1000]
            },
            "node_position": [400, 0]
        }

        response = send_command(sock, "add_blueprint_function_node", function_params)

        if not response or response.get("status") != "success":
            logger.error(f"Failed to add AddForce function node: {response}")
            return

        function_node_id = response.get("result", {}).get("node_id")
        logger.info(f"AddForce function node added successfully with ID: {function_node_id}")
        
        # Step 6: Connect BeginPlay to AddForce (execution)
        sock.close()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 55557))
        
        connect_exec_params = {
            "blueprint_name": "TestCompRefBP_"+random_suffix,
            "source_node_id": begin_play_node_id,
            "source_pin": "Then",  # Execution pin on BeginPlay
            "target_node_id": function_node_id,
            "target_pin": "Execute"  # Execution pin on function
        }
        
        response = send_command(sock, "connect_blueprint_nodes", connect_exec_params)
        if not response or response.get("status") != "success":
            logger.error(f"Failed to connect execution pins: {response}")
            return
            
        logger.info("Connected BeginPlay to AddForce execution pins!")
        
        # Step 8: Compile Blueprint
        sock.close()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 55557))
        
        compile_params = {
            "blueprint_name": "TestCompRefBP_"+random_suffix
        }
        
        response = send_command(sock, "compile_blueprint", compile_params)
        if not response or response.get("status") != "success":
            logger.error(f"Failed to compile blueprint: {response}")
            return
            
        logger.info("Blueprint compiled successfully!")
        
        # Step 9: Spawn the actor
        sock.close()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 55557))
        
        spawn_params = {
            "blueprint_name": "TestCompRefBP_"+random_suffix,
            "actor_name": "TestCompRefActor",
            "location": [0.0, 0.0, 100.0],
            "rotation": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0]
        }
        
        response = send_command(sock, "spawn_blueprint_actor", spawn_params)
        if not response or response.get("status") != "success":
            logger.error(f"Failed to spawn actor: {response}")
            return
            
        logger.info("Actor spawned successfully! The mesh should move up on BeginPlay.")
        
        sock.close()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 