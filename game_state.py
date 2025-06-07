"""
Game State Manager - Quản lý trạng thái game và giảm việc sử dụng biến global
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
import logging

logger = logging.getLogger("GameState")


class GamePhase(Enum):
    """Các giai đoạn của game"""
    MENU = "menu"
    CONNECTING = "connecting"
    WAITING_FOR_OPPONENT = "waiting_for_opponent"
    SHIP_PLACEMENT = "ship_placement"
    WAITING_FOR_OPPONENT_SHIPS = "waiting_for_opponent_ships"
    BATTLE = "battle"
    GAME_OVER = "game_over"


class GameMode(Enum):
    """Chế độ chơi"""
    SINGLEPLAYER = "singleplayer"
    MULTIPLAYER = "multiplayer"


class ConnectionStatus(Enum):
    """Trạng thái kết nối"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"


@dataclass
class PlayerState:
    """Trạng thái của người chơi"""
    name: str = "Player"
    ships: List[List[Tuple[int, int]]] = field(default_factory=list)
    hits_received: List[Tuple[int, int]] = field(default_factory=list)
    misses_received: List[Tuple[int, int]] = field(default_factory=list)
    ships_ready: bool = False
    wins: int = 0
    losses: int = 0


@dataclass
class NetworkState:
    """Trạng thái network"""
    connected: bool = False
    connection_status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    player_id: Optional[str] = None
    game_id: Optional[str] = None
    opponent_name: str = "Opponent"
    ping: int = 0
    last_message_time: float = 0


@dataclass
class BattleState:
    """Trạng thái trận đánh"""
    my_turn: bool = False
    shots_fired: List[Tuple[int, int, bool]] = field(default_factory=list)  # (x, y, hit)
    enemy_shots: List[Tuple[int, int, bool]] = field(default_factory=list)
    last_attack_coords: Optional[Tuple[int, int]] = None
    ships_remaining: Dict[str, List[int]] = field(default_factory=dict)  # player: [ship_sizes]


class GameState:
    """Singleton class quản lý toàn bộ trạng thái game"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GameState, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        
        # Game settings
        self.game_mode = GameMode.MULTIPLAYER
        self.game_phase = GamePhase.MENU
        self.ai_difficulty = "medium"
        
        # Player states
        self.player = PlayerState()
        self.opponent = PlayerState()
        
        # Network state
        self.network = NetworkState()
        
        # Battle state
        self.battle = BattleState()
        
        # UI state
        self.show_settings = False
        self.show_fps = False
        self.show_debug = False
        self.window_focused = True
        
        # Ship placement state
        self.ship_placement_phase = 0
        self.selected_ship_index = -1
        
        # Messages
        self.current_message = ""
        self.message_queue = []
        
        # AI instance
        self.ai_player = None
        
        # Settings
        self.volume_music = 50
        self.volume_effects = 50
        self.language = "EN"
        
        logger.info("GameState initialized")
    
    def reset(self):
        """Reset game state cho game mới"""
        # Reset player states
        self.player.ships.clear()
        self.player.hits_received.clear()
        self.player.misses_received.clear()
        self.player.ships_ready = False
        
        self.opponent.ships.clear()
        self.opponent.hits_received.clear()
        self.opponent.misses_received.clear()
        self.opponent.ships_ready = False
        
        # Reset battle state
        self.battle.my_turn = False
        self.battle.shots_fired.clear()
        self.battle.enemy_shots.clear()
        self.battle.last_attack_coords = None
        self.battle.ships_remaining.clear()
        
        # Reset network state for new game
        self.network.game_id = None
        self.network.opponent_name = "Opponent"
        
        # Reset phases
        self.game_phase = GamePhase.MENU
        self.ship_placement_phase = 0
        self.selected_ship_index = -1
        
        # Clear messages
        self.current_message = ""
        self.message_queue.clear()
        
        logger.info("Game state reset")
    
    def set_game_mode(self, mode: str):
        """Set game mode"""
        try:
            self.game_mode = GameMode(mode)
            logger.info(f"Game mode set to: {mode}")
        except ValueError:
            logger.error(f"Invalid game mode: {mode}")
    
    def set_game_phase(self, phase: str):
        """Set game phase"""
        try:
            old_phase = self.game_phase
            self.game_phase = GamePhase(phase)
            logger.info(f"Game phase changed from {old_phase.value} to {phase}")
        except ValueError:
            logger.error(f"Invalid game phase: {phase}")
    
    def is_singleplayer(self) -> bool:
        """Check if in singleplayer mode"""
        return self.game_mode == GameMode.SINGLEPLAYER
    
    def is_multiplayer(self) -> bool:
        """Check if in multiplayer mode"""
        return self.game_mode == GameMode.MULTIPLAYER
    
    def is_connected(self) -> bool:
        """Check if connected to server"""
        return self.network.connected and self.network.connection_status == ConnectionStatus.CONNECTED
    
    def is_in_game(self) -> bool:
        """Check if currently in a game"""
        return self.game_phase in [
            GamePhase.SHIP_PLACEMENT,
            GamePhase.WAITING_FOR_OPPONENT_SHIPS,
            GamePhase.BATTLE
        ]
    
    def is_battle_phase(self) -> bool:
        """Check if in battle phase"""
        return self.game_phase == GamePhase.BATTLE
    
    def add_player_ship(self, ship_positions: List[Tuple[int, int]]):
        """Add a ship to player's fleet"""
        self.player.ships.append(ship_positions)
        logger.info(f"Added ship with {len(ship_positions)} positions")
    
    def add_shot(self, x: int, y: int, hit: bool, is_player_shot: bool = True):
        """Record a shot"""
        if is_player_shot:
            self.battle.shots_fired.append((x, y, hit))
        else:
            self.battle.enemy_shots.append((x, y, hit))
    
    def get_player_shots(self) -> List[Tuple[int, int, bool]]:
        """Get all shots fired by player"""
        return self.battle.shots_fired
    
    def get_enemy_shots(self) -> List[Tuple[int, int, bool]]:
        """Get all shots fired by enemy"""
        return self.battle.enemy_shots
    
    def set_turn(self, is_my_turn: bool):
        """Set whose turn it is"""
        self.battle.my_turn = is_my_turn
        logger.info(f"Turn set to: {'Player' if is_my_turn else 'Opponent'}")
    
    def update_connection_status(self, status: str):
        """Update connection status"""
        try:
            self.network.connection_status = ConnectionStatus(status)
            self.network.connected = (status == "connected")
        except ValueError:
            logger.error(f"Invalid connection status: {status}")
    
    def set_network_info(self, player_id: str = None, game_id: str = None, 
                        opponent_name: str = None):
        """Update network information"""
        if player_id is not None:
            self.network.player_id = player_id
        if game_id is not None:
            self.network.game_id = game_id
        if opponent_name is not None:
            self.network.opponent_name = opponent_name
    
    def save_settings(self):
        """Save game settings to file"""
        import json
        import os
        
        settings = {
            "volume": f"{self.volume_music},{self.volume_effects}",
            "language": self.language,
            "name": self.player.name,
            "wins": self.player.wins,
            "losses": self.player.losses
        }
        
        try:
            with open(os.path.join("settings", "preferences.json"), "w") as f:
                json.dump(settings, f, indent=4)
            logger.info("Settings saved successfully")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
    
    def load_settings(self):
        """Load game settings from file"""
        import json
        import os
        
        try:
            with open(os.path.join("settings", "preferences.json"), "r") as f:
                settings = json.load(f)
                
            # Load volumes
            volumes = settings.get("volume", "50,50").split(",")
            self.volume_music = int(volumes[0]) if len(volumes) > 0 else 50
            self.volume_effects = int(volumes[1]) if len(volumes) > 1 else 50
            
            # Load other settings
            self.language = settings.get("language", "EN")
            self.player.name = settings.get("name", "Player")
            self.player.wins = int(settings.get("wins", 0))
            self.player.losses = int(settings.get("losses", 0))
            
            logger.info("Settings loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            # Use default values
            self.volume_music = 50
            self.volume_effects = 50
            self.language = "EN"
            self.player.name = "Player"
    
    def add_win(self):
        """Increment win counter"""
        self.player.wins += 1
        self.save_settings()
    
    def add_loss(self):
        """Increment loss counter"""
        self.player.losses += 1
        self.save_settings()


# Tạo instance singleton
game_state = GameState()