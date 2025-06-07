"""
Game Integration Module - Connects all game components together
"""

import logging
from typing import Optional
from game_state import game_state, GamePhase, GameMode
from network_manager import NetworkManager, MessageType
from ui_manager import UIManager
from ship_manager import ShipManager
from battle_manager import BattleManager
import ai

logger = logging.getLogger("GameIntegration")


class GameIntegration:
    """Integrates all game components and handles communication between them"""
    
    def __init__(self, ui_manager: UIManager, ship_manager: ShipManager, 
                 battle_manager: BattleManager):
        self.ui_manager = ui_manager
        self.ship_manager = ship_manager
        self.battle_manager = battle_manager
        self.network_manager: Optional[NetworkManager] = None
        
        # Set up UI callbacks
        self._setup_ui_callbacks()
        
        logger.info("GameIntegration initialized")
    
    def _setup_ui_callbacks(self):
        """Override UI manager callbacks to handle game logic"""
        # Override start game callback
        self.ui_manager.on_start_game = self._on_start_game
        
        # Override ships done callback
        self.ui_manager.on_ships_done = self._on_ships_done
    
    def _on_start_game(self):
        """Handle start game from UI"""
        logger.info(f"Starting game in {game_state.game_mode.value} mode")
        
        if game_state.is_singleplayer():
            # Initialize AI
            self._initialize_ai()
            game_state.set_game_phase("ship_placement")
            self.ui_manager.show_message("Place your ships", 3.0, "info")
        else:
            # Initialize network
            game_state.set_game_phase("connecting")
            self.ui_manager.show_message("Connecting to server...", 3.0, "info")
            self._initialize_network()
    
    def _on_ships_done(self):
        """Handle ships placement done"""
        logger.info("Checking ship placement...")
        
        if self.ship_manager.place_all_ships():
            self.ui_manager.show_message("Ships placed successfully!", 2.0, "success")
            
            if game_state.is_singleplayer():
                # Generate AI ships
                self.ship_manager.generate_random_enemy_ships()
                # Start battle
                game_state.set_game_phase("battle")
                game_state.set_turn(True)  # Player goes first
                self.ui_manager.show_message("Battle begins!", 2.0, "info")
            else:
                # Send ready message and wait for opponent
                game_state.set_game_phase("waiting_for_opponent_ships")
                if self.network_manager and game_state.is_connected():
                    self.network_manager.notify_ships_ready()
                    self.ui_manager.show_message("Waiting for opponent...", 3.0, "info")
        else:
            self.ui_manager.show_message("Invalid ship placement!", 2.0, "error")
    
    def _initialize_ai(self):
        """Initialize AI player based on difficulty"""
        ai_classes = {
            "easy": ai.RandomAI,
            "medium": ai.HuntTargetAI,
            "hard": ai.ProbabilityAI,
            "expert": ai.AlphaBetaAI,
            "master": ai.MCTSAI
        }
        
        ai_class = ai_classes.get(game_state.ai_difficulty, ai.HuntTargetAI)
        game_state.ai_player = ai_class()
        
        # Set opponent name
        game_state.network.opponent_name = f"AI ({game_state.ai_difficulty.capitalize()})"
        
        logger.info(f"AI initialized: {ai_class.__name__}")
    
    def _initialize_network(self):
        """Initialize network connection"""
        if self.network_manager:
            # Already initialized
            return
            
        self.network_manager = NetworkManager()
        
        # Set up connection listener
        self.network_manager.add_connection_listener(self._on_connection_changed)
        
        # Set up message handlers
        self._setup_network_handlers()
        
        # Load server settings
        import json
        import os
        
        try:
            with open(os.path.join("settings", "settings.json")) as f:
                settings = json.load(f)
                
            host = settings.get("serverip", "127.0.0.1")
            port = settings.get("serverport", 8888)
            
            if not host:
                host = "127.0.0.1"
                
        except Exception as e:
            logger.error(f"Failed to load server settings: {e}")
            host = "127.0.0.1"
            port = 8888
        
        # Connect
        if self.network_manager.connect(host, port):
            # Look for game
            self.network_manager.look_for_game(game_state.player.name)
            game_state.set_game_phase("waiting_for_opponent")
            self.ui_manager.show_message("Looking for opponent...", 5.0, "info")
        else:
            self.ui_manager.show_message("Failed to connect to server", 3.0, "error")
            self._return_to_menu()
    
    def _setup_network_handlers(self):
        """Set up network message handlers"""
        handlers = {
            MessageType.GAME_START: self._on_game_start,
            MessageType.SHIPS_READY: self._on_opponent_ready,
            MessageType.ATTACK: self._on_attack_received,
            MessageType.ATTACK_RESULT: self._on_attack_result,
            MessageType.WIN: self._on_opponent_win,
            MessageType.LOGOUT: self._on_opponent_left,
            MessageType.SERVER_SHUTDOWN: self._on_server_shutdown
        }
        
        for msg_type, handler in handlers.items():
            self.network_manager.add_message_handler(msg_type, handler)
    
    def _on_connection_changed(self, connected: bool):
        """Handle connection status change"""
        if connected:
            game_state.update_connection_status("connected")
            self.ui_manager.show_message("Connected to server", 2.0, "success")
        else:
            game_state.update_connection_status("disconnected")
            
            if game_state.is_in_game():
                self.ui_manager.show_message("Connection lost!", 3.0, "error")
                self._return_to_menu()
    
    def _on_game_start(self, data: dict):
        """Handle game start message"""
        game_state.set_network_info(
            game_id=data["game_id"],
            opponent_name=data["opponent_name"]
        )
        game_state.set_game_phase("ship_placement")
        self.ui_manager.show_message(f"Game started with {data['opponent_name']}", 3.0, "info")
        logger.info(f"Game started - ID: {data['game_id']}, Opponent: {data['opponent_name']}")
    
    def _on_opponent_ready(self, data: dict):
        """Handle opponent ships ready"""
        game_state.opponent.ships_ready = True
        self.ui_manager.show_message("Opponent is ready!", 2.0, "info")
        
        # If we're also ready, start battle
        if game_state.player.ships_ready:
            game_state.set_game_phase("battle")
            game_state.set_turn(True)  # Could be randomized
            self.ui_manager.show_message("Battle begins!", 2.0, "info")
    
    def _on_attack_received(self, data: dict):
        """Handle incoming attack"""
        x = data["x"]
        y = data["y"]
        
        logger.info(f"Received attack at ({x}, {y})")
        
        # Process attack
        hit, sunk, ship_size = self.ship_manager.handle_shot(x, y, False)
        
        # Add to battle manager
        self.battle_manager.process_enemy_shot(x, y)
        
        # Send result back
        if self.network_manager:
            self.network_manager.send_attack_result(x, y, hit, sunk, ship_size)
        
        # Check for game over
        winner = self.ship_manager.check_game_over()
        if winner == "enemy":
            self._handle_defeat()
        else:
            # Switch turns
            game_state.set_turn(True)
    
    def _on_attack_result(self, data: dict):
        """Handle attack result from opponent"""
        x = data["x"]
        y = data["y"]
        hit = data["hit"]
        sunk = data.get("sunk", False)
        ship_size = data.get("ship_size")
        
        logger.info(f"Attack result at ({x}, {y}): {'HIT' if hit else 'MISS'}")
        
        # Update our shot record
        for shot in self.battle_manager.shots:
            if shot.x == x and shot.y == y and shot.player_shot:
                shot.hit = hit
                break
        
        # Update enemy ship if sunk
        if sunk and ship_size:
            # Mark enemy ship as sunk
            for ship in self.ship_manager.enemy_ships:
                if ship.size == ship_size and not ship.is_sunk:
                    ship.is_sunk = True
                    break
        
        # Play sound
        self.battle_manager.play_shot_sound(hit, sunk)
        
        # Show message
        if sunk:
            self.ui_manager.show_message(f"Enemy ship sunk! (size {ship_size})", 3.0, "success")
        elif hit:
            self.ui_manager.show_message("Hit!", 1.5, "success")
        else:
            self.ui_manager.show_message("Miss!", 1.5, "info")
        
        # Check for victory
        winner = self.ship_manager.check_game_over()
        if winner == "player":
            self._handle_victory()
        else:
            # Switch turns
            game_state.set_turn(False)
    
    def _on_opponent_win(self, data: dict):
        """Handle opponent victory"""
        logger.info("Opponent won the game")
        self._handle_defeat()
    
    def _on_opponent_left(self, data: dict):
        """Handle opponent disconnect"""
        logger.info("Opponent left the game")
        self.ui_manager.show_message("Opponent left the game!", 5.0, "warning")
        self._handle_victory()
    
    def _on_server_shutdown(self, data: dict):
        """Handle server shutdown"""
        logger.warning("Server is shutting down")
        self.ui_manager.show_message("Server is shutting down", 5.0, "error")
        self._return_to_menu()
    
    def handle_battle_action(self, x: int, y: int):
        """Handle player attack in battle phase"""
        if not game_state.battle.my_turn:
            return
            
        logger.info(f"Player attacking at ({x}, {y})")
        
        if game_state.is_singleplayer():
            # Process attack immediately
            self.battle_manager.process_player_shot(x, y)
        else:
            # Send attack to server
            if self.network_manager and game_state.is_connected():
                self.network_manager.send_attack(x, y)
                
                # Add pending shot marker
                from battle_manager import Shot
                shot = Shot(x, y, False, True)
                self.battle_manager.shots.append(shot)
                
                # Don't switch turns yet - wait for response
                self.ui_manager.show_message("Firing...", 1.0, "info")
    
    def handle_ai_turn(self):
        """Handle AI turn in singleplayer"""
        if not game_state.is_singleplayer() or game_state.battle.my_turn:
            return
            
        self.battle_manager.handle_ai_turn()
    
    def update(self):
        """Update integration logic"""
        # Process network messages
        if self.network_manager and game_state.is_multiplayer():
            self.network_manager.process_messages()
        
        # Handle battle input
        if game_state.is_battle_phase() and game_state.battle.my_turn:
            import pygame
            mouse_pos = pygame.mouse.get_pos()
            mouse_clicked = pygame.mouse.get_pressed()[0]
            
            if mouse_clicked:
                # Check if clicked on enemy grid
                grid_pos = self.ship_manager.get_grid_position(mouse_pos, False)
                if grid_pos:
                    x, y = grid_pos
                    # Check if not already shot
                    if not self.battle_manager.is_position_shot(x, y, True):
                        self.handle_battle_action(x, y)
    
    def _handle_victory(self):
        """Handle game victory"""
        game_state.add_win()
        game_state.set_game_phase("game_over")
        self.ui_manager.show_message("Victory! You won the game!", 5.0, "success")
        
        # Send win message if multiplayer
        if self.network_manager and game_state.is_multiplayer():
            self.network_manager.send_win()
    
    def _handle_defeat(self):
        """Handle game defeat"""
        game_state.add_loss()
        game_state.set_game_phase("game_over")
        self.ui_manager.show_message("Defeat! You lost the game.", 5.0, "error")
    
    def _return_to_menu(self):
        """Return to main menu"""
        # Disconnect if connected
        if self.network_manager and game_state.is_connected():
            self.network_manager.disconnect()
            self.network_manager = None
        
        # Reset game state
        game_state.reset()
        
        # Reset managers
        self.ship_manager.__init__()
        self.battle_manager.reset()
        
        logger.info("Returned to main menu")