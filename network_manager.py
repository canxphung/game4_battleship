"""
Network Manager - Improved network communication with better error handling
"""

import socket
import threading
import time
import json
import queue
import logging
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("NetworkManager")


class MessageType(Enum):
    """Network message types"""
    # Connection
    ID_REQUEST = "id_request"
    HEARTBEAT = "heartbeat"
    
    # Matchmaking
    LOOKING_FOR_GAME = "lfg"
    GAME_START = "start"
    
    # Game setup
    SHIPS_READY = "ships_ready"
    
    # Battle
    ATTACK = "attack"
    ATTACK_RESULT = "attack_result"
    
    # Game end
    WIN = "win"
    SURRENDER = "surrender"
    LOGOUT = "logout"
    
    # Server
    SERVER_SHUTDOWN = "server_shutdown"
    ERROR = "error"


@dataclass
class NetworkMessage:
    """Network message structure"""
    msg_type: MessageType
    data: Dict[str, Any]
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
    
    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps({
            "type": self.msg_type.value,
            "data": self.data,
            "timestamp": self.timestamp
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'NetworkMessage':
        """Create message from JSON string"""
        try:
            data = json.loads(json_str)
            return cls(
                msg_type=MessageType(data["type"]),
                data=data.get("data", {}),
                timestamp=data.get("timestamp", time.time())
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse message: {json_str}, error: {e}")
            raise


class NetworkManager:
    """Manages all network communication"""
    
    def __init__(self):
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.player_id: Optional[str] = None
        self.game_id: Optional[str] = None
        
        # Threading
        self.receive_thread: Optional[threading.Thread] = None
        self.send_thread: Optional[threading.Thread] = None
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.running = False
        
        # Message queues
        self.send_queue: queue.Queue[NetworkMessage] = queue.Queue()
        self.receive_queue: queue.Queue[NetworkMessage] = queue.Queue()
        
        # Message handlers
        self.message_handlers: Dict[MessageType, List[Callable]] = {}
        
        # Connection listeners
        self.connection_listeners: List[Callable[[bool], None]] = []
        
        # Settings
        self.heartbeat_interval = 30  # seconds
        self.receive_timeout = 1.0    # seconds
        self.last_heartbeat = 0
        self.ping = 0
        
        logger.info("NetworkManager initialized")
    
    def connect(self, host: str, port: int, timeout: float = 5.0) -> bool:
        """Connect to game server"""
        try:
            # Create socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(timeout)
            
            logger.info(f"Connecting to {host}:{port}...")
            self.socket.connect((host, port))
            
            # Request player ID
            self.socket.sendall(b"ID Required")
            data = self.socket.recv(2048)
            
            if not data:
                raise ConnectionError("No response from server")
            
            self.player_id = data.decode('utf-8').strip()
            logger.info(f"Received player ID: {self.player_id}")
            
            # Set socket to non-blocking for receive thread
            self.socket.settimeout(self.receive_timeout)
            
            # Start threads
            self.running = True
            self.connected = True
            
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.send_thread = threading.Thread(target=self._send_loop, daemon=True)
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            
            self.receive_thread.start()
            self.send_thread.start()
            self.heartbeat_thread.start()
            
            # Notify listeners
            self._notify_connection_listeners(True)
            
            logger.info("Successfully connected to server")
            return True
            
        except (socket.timeout, ConnectionRefusedError, ConnectionError) as e:
            logger.error(f"Connection failed: {e}")
            self._cleanup_socket()
            return False
        except Exception as e:
            logger.error(f"Unexpected connection error: {e}")
            self._cleanup_socket()
            return False
    
    def disconnect(self):
        """Disconnect from server"""
        logger.info("Disconnecting from server...")
        
        # Send logout message
        if self.connected:
            try:
                self.send_message(MessageType.LOGOUT, {})
                time.sleep(0.1)  # Give time to send
            except:
                pass
        
        # Stop threads
        self.running = False
        self.connected = False
        
        # Wait for threads to finish
        for thread in [self.receive_thread, self.send_thread, self.heartbeat_thread]:
            if thread and thread.is_alive():
                thread.join(timeout=1.0)
        
        # Cleanup socket
        self._cleanup_socket()
        
        # Clear queues
        while not self.send_queue.empty():
            try:
                self.send_queue.get_nowait()
            except:
                pass
                
        while not self.receive_queue.empty():
            try:
                self.receive_queue.get_nowait()
            except:
                pass
        
        # Notify listeners
        self._notify_connection_listeners(False)
        
        logger.info("Disconnected from server")
    
    def send_message(self, msg_type: MessageType, data: Dict[str, Any]):
        """Send a message to the server"""
        if not self.connected:
            logger.warning("Cannot send message: not connected")
            return
        
        message = NetworkMessage(msg_type, data)
        self.send_queue.put(message)
        logger.debug(f"Queued message: {msg_type.value}")
    
    def process_messages(self):
        """Process received messages (call from main thread)"""
        processed = 0
        
        while not self.receive_queue.empty() and processed < 10:  # Limit per frame
            try:
                message = self.receive_queue.get_nowait()
                self._handle_message(message)
                processed += 1
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    def add_message_handler(self, msg_type: MessageType, handler: Callable):
        """Add a handler for a specific message type"""
        if msg_type not in self.message_handlers:
            self.message_handlers[msg_type] = []
        
        if handler not in self.message_handlers[msg_type]:
            self.message_handlers[msg_type].append(handler)
            logger.debug(f"Added handler for {msg_type.value}")
    
    def remove_message_handler(self, msg_type: MessageType, handler: Callable):
        """Remove a message handler"""
        if msg_type in self.message_handlers:
            if handler in self.message_handlers[msg_type]:
                self.message_handlers[msg_type].remove(handler)
                logger.debug(f"Removed handler for {msg_type.value}")
    
    def add_connection_listener(self, listener: Callable[[bool], None]):
        """Add a connection status listener"""
        if listener not in self.connection_listeners:
            self.connection_listeners.append(listener)
    
    def remove_connection_listener(self, listener: Callable[[bool], None]):
        """Remove a connection listener"""
        if listener in self.connection_listeners:
            self.connection_listeners.remove(listener)
    
    # Game-specific message methods
    def look_for_game(self, player_name: str):
        """Look for a game match"""
        self.send_message(MessageType.LOOKING_FOR_GAME, {
            "name": player_name
        })
    
    def notify_ships_ready(self):
        """Notify that ships are placed"""
        self.send_message(MessageType.SHIPS_READY, {})
    
    def send_attack(self, x: int, y: int):
        """Send an attack"""
        self.send_message(MessageType.ATTACK, {
            "x": x,
            "y": y,
            "game_id": self.game_id
        })
    
    def send_attack_result(self, x: int, y: int, hit: bool, 
                          sunk: bool = False, ship_size: Optional[int] = None):
        """Send attack result"""
        data = {
            "x": x,
            "y": y,
            "hit": hit,
            "sunk": sunk,
            "game_id": self.game_id
        }
        
        if ship_size is not None:
            data["ship_size"] = ship_size
            
        self.send_message(MessageType.ATTACK_RESULT, data)
    
    def send_win(self):
        """Notify that we won"""
        self.send_message(MessageType.WIN, {"game_id": self.game_id})
    
    def send_surrender(self):
        """Surrender the game"""
        self.send_message(MessageType.SURRENDER, {"game_id": self.game_id})
    
    # Private methods
    def _receive_loop(self):
        """Receive messages from server"""
        logger.info("Receive thread started")
        buffer = ""
        
        while self.running:
            try:
                # Receive data
                data = self.socket.recv(4096)
                
                if not data:
                    logger.warning("Server disconnected")
                    self.connected = False
                    self._notify_connection_listeners(False)
                    break
                
                # Add to buffer
                buffer += data.decode('utf-8')
                
                # Process complete messages (separated by newlines)
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    
                    if not line:
                        continue
                    
                    try:
                        # Parse legacy format first
                        message = self._parse_legacy_message(line)
                        if message:
                            self.receive_queue.put(message)
                        else:
                            # Try JSON format
                            message = NetworkMessage.from_json(line)
                            self.receive_queue.put(message)
                    except Exception as e:
                        logger.error(f"Failed to parse message: {line}, error: {e}")
                        
            except socket.timeout:
                continue
            except ConnectionResetError:
                logger.error("Connection reset by server")
                self.connected = False
                self._notify_connection_listeners(False)
                break
            except Exception as e:
                logger.error(f"Receive error: {e}")
                if self.running:
                    time.sleep(0.1)
        
        logger.info("Receive thread stopped")
    
    def _send_loop(self):
        """Send messages to server"""
        logger.info("Send thread started")
        
        while self.running:
            try:
                # Get message from queue
                message = self.send_queue.get(timeout=0.1)
                
                if not self.connected or not self.socket:
                    continue
                
                # Format message
                formatted = self._format_message(message)
                
                # Send
                self.socket.sendall(formatted.encode('utf-8') + b'\n')
                logger.debug(f"Sent: {formatted}")
                
            except queue.Empty:
                continue
            except BrokenPipeError:
                logger.error("Broken pipe - server disconnected")
                self.connected = False
                self._notify_connection_listeners(False)
                break
            except Exception as e:
                logger.error(f"Send error: {e}")
                if self.running:
                    time.sleep(0.1)
        
        logger.info("Send thread stopped")
    
    def _heartbeat_loop(self):
        """Send periodic heartbeats"""
        logger.info("Heartbeat thread started")
        
        while self.running:
            try:
                if self.connected and time.time() - self.last_heartbeat > self.heartbeat_interval:
                    # Measure ping
                    start_time = time.time()
                    self.send_message(MessageType.HEARTBEAT, {})
                    self.last_heartbeat = time.time()
                    
                    # Update ping (will be calculated when response received)
                    self._heartbeat_start_time = start_time
                
                time.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
        
        logger.info("Heartbeat thread stopped")
    
    def _format_message(self, message: NetworkMessage) -> str:
        """Format message for sending"""
        # Use legacy format for compatibility
        if message.msg_type == MessageType.LOOKING_FOR_GAME:
            return f"{self.player_id}:lfg.{message.data['name']}"
        elif message.msg_type == MessageType.SHIPS_READY:
            return f"{self.player_id}:1:{self.game_id}"
        elif message.msg_type == MessageType.ATTACK:
            return f"{self.player_id}:attack.({message.data['x']},{message.data['y']}):{self.game_id}"
        elif message.msg_type == MessageType.ATTACK_RESULT:
            result = f"{self.player_id}:guessAnswer.{message.data['hit']}.{message.data['x']}.{message.data['y']}"
            if message.data.get('sunk'):
                result += f".sunk.{message.data.get('ship_size', 0)}"
            return result + f":{self.game_id}"
        elif message.msg_type == MessageType.WIN:
            return f"{self.player_id}:win:{self.game_id}"
        elif message.msg_type == MessageType.LOGOUT:
            return f"{self.player_id}:logout"
        elif message.msg_type == MessageType.HEARTBEAT:
            return f"{self.player_id}:heartbeat"
        else:
            # Default to JSON format
            return message.to_json()
    
    def _parse_legacy_message(self, message: str) -> Optional[NetworkMessage]:
        """Parse legacy message format"""
        try:
            # Handle simple messages
            if message == "heartbeat":
                # Calculate ping
                if hasattr(self, '_heartbeat_start_time'):
                    self.ping = int((time.time() - self._heartbeat_start_time) * 1000)
                return NetworkMessage(MessageType.HEARTBEAT, {"ping": self.ping})
            elif message == "logout":
                return NetworkMessage(MessageType.LOGOUT, {})
            elif message == "win":
                return NetworkMessage(MessageType.WIN, {})
            elif message == "server_shutdown":
                return NetworkMessage(MessageType.SERVER_SHUTDOWN, {})
            
            # Handle complex messages
            if ":" in message:
                parts = message.split(":")
                
                # Game start: start:game_id:opponent_name
                if parts[0] == "start" and len(parts) >= 3:
                    self.game_id = parts[1]
                    return NetworkMessage(MessageType.GAME_START, {
                        "game_id": parts[1],
                        "opponent_name": parts[2]
                    })
                
                # Ships ready from opponent
                elif len(parts) >= 2 and parts[1] == "1":
                    return NetworkMessage(MessageType.SHIPS_READY, {
                        "opponent": True
                    })
            
            # Handle dot-separated messages
            elif "." in message:
                parts = message.split(".")
                
                # Attack: attack.(x,y)
                if parts[0] == "attack" and len(parts) >= 2:
                    coords = parts[1].strip("()")
                    x, y = map(int, coords.split(","))
                    return NetworkMessage(MessageType.ATTACK, {
                        "x": x,
                        "y": y,
                        "opponent": True
                    })
                
                # Attack result: guessAnswer.hit.x.y[.sunk.size]
                elif parts[0] == "guessAnswer" and len(parts) >= 4:
                    data = {
                        "hit": parts[1] == "True",
                        "x": int(parts[2]),
                        "y": int(parts[3]),
                        "opponent": False
                    }
                    
                    if len(parts) > 4 and parts[4] == "sunk":
                        data["sunk"] = True
                        if len(parts) > 5:
                            data["ship_size"] = int(parts[5])
                    
                    return NetworkMessage(MessageType.ATTACK_RESULT, data)
            
            logger.warning(f"Unknown message format: {message}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to parse legacy message: {message}, error: {e}")
            return None
    
    def _handle_message(self, message: NetworkMessage):
        """Handle a received message"""
        logger.debug(f"Handling message: {message.msg_type.value}")
        
        # Call registered handlers
        if message.msg_type in self.message_handlers:
            for handler in self.message_handlers[message.msg_type]:
                try:
                    handler(message.data)
                except Exception as e:
                    logger.error(f"Handler error for {message.msg_type.value}: {e}")
    
    def _notify_connection_listeners(self, connected: bool):
        """Notify all connection listeners"""
        for listener in self.connection_listeners:
            try:
                listener(connected)
            except Exception as e:
                logger.error(f"Connection listener error: {e}")
    
    def _cleanup_socket(self):
        """Clean up socket resources"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None